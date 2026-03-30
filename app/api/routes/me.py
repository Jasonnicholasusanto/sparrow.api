from uuid import UUID
import uuid
from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Response,
    UploadFile,
    status,
)

from sqlalchemy.exc import IntegrityError
from app.api.dependencies.profile import get_current_profile
from app.api.deps import CurrentUser, SessionDep
from app.schemas.user_activity import UserActivityCreate, UserActivityPublic
from app.schemas.user_detail import UserDetailsResponse
from app.schemas.user_follow import PaginatedFollowersResponse
from app.schemas.user_profile import (
    UserProfileCreate,
    UserProfileMe,
    UserProfilePublic,
    UserProfileUpdate,
    UserProfileUpdateEmail,
)
from app.services.user_profile_service import (
    _email_exists,
    _username_exists,
    create_user_profile,
    get_user_profile_by_auth,
    update_user_background_picture,
    update_user_email_address,
    update_user_profile,
    update_user_profile_picture,
)
from app.services.user_activity_service import (
    get_user_activity,
    create_user_activity,
)
from app.services.user_follow_service import (
    get_followers,
    get_followers_count,
    get_following,
    get_following_count,
)
from app.utils.functions import extract_storage_path
from app.utils.global_variables import (
    MAX_PROFILE_PICTURE_FILE_SIZE_KB,
    RESERVED,
    MAX_BANNER_IMAGE_FILE_SIZE_KB,
)
from app.core.db import supabase_client


router = APIRouter(prefix="/me", tags=["Me"])


# Authenticated: Get my a logged in user's profile
@router.get("/profile", response_model=UserDetailsResponse)
def get_my_profile(
    db: SessionDep,
    user=Depends(get_current_profile),
):
    """
    Return the profile of the currently authenticated user.
    - `user` is injected from JWT (CurrentUser).
    - If no profile exists yet, return 404.
    """
    # auth user id from JWT dependency; handle either .user_id or .id
    auth_user_id = getattr(user, "user_id", None) or getattr(user, "id", None)
    if not auth_user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")

    # 1. Activity by user_id (PK)
    activity = get_user_activity(db, profile_id=user.id)
    if not activity:
        activity = create_user_activity(
            db,
            profile_id=user.id,
            obj_in=UserActivityCreate(),
        )

    # 2. Followers and Following counts
    followers_count = get_followers_count(db, user_id=user.id)
    following_count = get_following_count(db, user_id=user.id)

    return UserDetailsResponse(
        profile=UserProfileMe.model_validate(user, from_attributes=True),
        activity=UserActivityPublic.model_validate(activity, from_attributes=True)
        if activity
        else None,
        followers_count=followers_count or 0,
        following_count=following_count or 0,
    )


@router.get("/followers", response_model=PaginatedFollowersResponse)
def list_followers(
    user=Depends(get_current_profile),
    db: SessionDep = None,
    limit: int = 20,
    offset: int = 0,
):
    """
    Returns list of users who follow the given user.
    """
    # auth user id from JWT dependency; handle either .user_id or .id
    auth_user_id = getattr(user, "user_id", None) or getattr(user, "id", None)
    if not auth_user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")

    total = get_followers_count(db, user.id)
    followers = get_followers(db, user.id, limit=limit, offset=offset)
    return PaginatedFollowersResponse(
        total=total,
        limit=limit,
        offset=offset,
        data=[
            UserProfilePublic.model_validate(u, from_attributes=True) for u in followers
        ],
    )


@router.get("/following", response_model=PaginatedFollowersResponse)
def list_following(
    user=Depends(get_current_profile),
    db: SessionDep = None,
    limit: int = 20,
    offset: int = 0,
):
    """
    Returns list of users the given user is following.
    """
    # auth user id from JWT dependency; handle either .user_id or .id
    auth_user_id = getattr(user, "user_id", None) or getattr(user, "id", None)
    if not auth_user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")

    total = get_following_count(db, user.id)
    following = get_following(db, user.id, limit=limit, offset=offset)
    return PaginatedFollowersResponse(
        total=total,
        limit=limit,
        offset=offset,
        data=[
            UserProfilePublic.model_validate(u, from_attributes=True) for u in following
        ],
    )


# Authenticated: Create my user profile
@router.post(
    "/profile", response_model=UserProfilePublic, status_code=status.HTTP_201_CREATED
)
def create_my_profile(
    payload: UserProfileCreate,
    db: SessionDep,
    user: CurrentUser,
):
    """
    Create the current user's profile after authentication/onboarding.
    - Derives auth_id and email from the authenticated user.
    - Enforces unique username and email collisions (409).
    - Fails if the profile already exists (409).
    """

    # 1) Guard: reserved usernames
    if payload.username and payload.username.lower() in RESERVED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Username is reserved"
        )

    # 2) Prevent duplicate creation for the same auth_id
    if get_user_profile_by_auth(db, auth_id=user.id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="User Profile already exists"
        )

    # 3) Prevent duplicate username
    exists = _username_exists(session=db, username=payload.username)
    if exists:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Username already taken"
        )

    # 4) Build the create DTO (server never accepts auth_id from client)
    profile_in = UserProfileCreate(**payload.model_dump(exclude_unset=True))
    profile_in.email_address = user.email

    # 5) Create via user profile service
    try:
        profile = create_user_profile(
            db,
            auth_id=UUID(str(user.id)),
            profile_in=profile_in,
        )
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username, phone number, or email already in use",
        )

    # 6) Ensure profile creation succeeded
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create profile",
        )

    # 7) Create an empty activity record for the new user
    try:
        activity = get_user_activity(db, profile_id=profile.id)
        if not activity:
            activity = create_user_activity(
                db,
                profile_id=profile.id,
                obj_in=UserActivityCreate(),
            )
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Failed to create user activity",
        )

    # 8) Ensure activity creation succeeded
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user activity",
        )

    return UserProfilePublic.model_validate(profile, from_attributes=True)


# Authenticated: Update a logged in user's profile
@router.patch("/profile", response_model=UserProfileMe)
def update_my_profile(
    update: UserProfileUpdate,
    db: SessionDep,
    user=Depends(get_current_profile),
):
    """
    Partially update the authenticated user's profile.
    Only fields provided in the request body will be updated.
    """

    # Prevent reserved usernames
    if update.username and update.username.lower() in RESERVED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username is reserved",
        )

    # 2b) Prevent duplicate username
    if update.username and update.username != user.username:
        exists = _username_exists(session=db, username=update.username)
        if exists:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Username already taken"
            )

    # 3) Update via service
    try:
        profile = update_user_profile(db, user_id=user.id, profile_update=update)
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username or phone number already in use",
        )

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server error updating profile",
        )

    return UserProfileMe.model_validate(profile, from_attributes=True)


@router.patch("/update-email", status_code=status.HTTP_200_OK)
def update_user_email(
    db: SessionDep,
    update: UserProfileUpdateEmail,
    user=Depends(get_current_profile),
):
    """
    Update the authenticated user's email address in both:
      - public.user_profile (local DB)
      - auth.users (Supabase Auth)
    """
    email_exists = _email_exists(session=db, email=update.email_address)

    if email_exists:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email address is already in use.",
        )

    # 1. Validate the new email
    if user.email_address.lower() == update.email_address.lower():
        raise HTTPException(
            status_code=400,
            detail="The new email address is the same as the current one.",
        )

    # 2. Update email in Supabase Auth
    try:
        res = supabase_client.auth.admin.update_user_by_id(
            user.id,
            {"email": update.email_address},
        )
        if not res.user:
            raise Exception("No user returned from Supabase after update.")
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to update email in Supabase Auth: {str(e)}"
        )

    # 3. Update DB (public.user_profile)
    try:
        profile = update_user_email_address(db, user_id=user.id, email_update=update)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update email in local database: {str(e)}",
        )

    return {
        "message": "Email address updated successfully.",
        "profile": profile,
    }


# Authenticated: Upload banner picture
@router.post("/upload-banner-image")
async def upload_banner_image(
    db: SessionDep,
    file: UploadFile = File(...),
    user=Depends(get_current_profile),
):
    """
    Uploads a profile picture for the current user to Supabase Storage,
    updates the user_profile table with the public URL, and returns it.
    """

    # 1. Validate file type
    if not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only image uploads are allowed.",
        )

    # 2. Validate file size
    contents = await file.read()
    if len(contents) > MAX_BANNER_IMAGE_FILE_SIZE_KB * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large (max {MAX_BANNER_IMAGE_FILE_SIZE_KB} KB).",
        )

    # 3. Generate unique filename
    ext = file.filename.split(".")[-1]
    unique_filename = f"{user.id}-{uuid.uuid4().hex}.{ext}"
    file_path = f"{user.id}/{unique_filename}"

    # 4. Upload to Supabase Storage
    supabase_client.storage.from_("banner-images").upload(
        path=file_path,
        file=contents,
        file_options={"cache-control": "3600", "upsert": "false"},
    )

    # 5. Delete old banner picture (if exists)
    if user.background_picture:
        old_path = extract_storage_path(user.background_picture, "banner-images")
        if old_path and old_path.startswith(str(user.id)):
            supabase_client.storage.from_("banner-images").remove([old_path])

    # 6. Get public URL
    public_url = supabase_client.storage.from_("banner-images").get_public_url(
        file_path
    )

    # 7. Update DB with new URL
    try:
        update_user_background_picture(db, user_id=user.id, background_url=public_url)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update banner image URL in database: {str(e)}",
        )

    return {"banner_image_url": public_url}


@router.delete("/delete-banner-image")
async def delete_banner_image(
    db: SessionDep,
    user=Depends(get_current_profile),
):
    """
    Deletes all profile pictures of the current user from Supabase Storage,
    and sets `profile_picture` to NULL in the `user_profile` table.
    """

    user_folder = str(user.id)

    # 1. List all files in this user's folder inside "banner-images" bucket
    try:
        list_res = supabase_client.storage.from_("banner-images").list(path=user_folder)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list user's profile pictures: {str(e)}",
        )

    # 2 Delete all files found
    if list_res:
        file_paths = [f"{user_folder}/{item['name']}" for item in list_res]
        try:
            supabase_client.storage.from_("banner-images").remove(file_paths)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete files from storage: {str(e)}",
            )

    # 4. Update database to set background_picture = NULL
    try:
        update_user_background_picture(db, user_id=user.id, background_url=None)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update banner image in database: {str(e)}",
        )

    return {"message": "Banner image deleted successfully."}


# Authenticated: Upload profile picture
@router.post("/upload-profile-picture")
async def upload_profile_picture(
    db: SessionDep,
    file: UploadFile = File(...),
    user=Depends(get_current_profile),
):
    """
    Uploads a profile picture for the current user to Supabase Storage,
    updates the user_profile table with the public URL, and returns it.
    """

    # 1. Validate file type
    if not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only image uploads are allowed.",
        )

    # 2. Validate file size
    contents = await file.read()
    if len(contents) > MAX_PROFILE_PICTURE_FILE_SIZE_KB * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large (max {MAX_PROFILE_PICTURE_FILE_SIZE_KB} KB).",
        )

    # 3. Generate unique filename
    ext = file.filename.split(".")[-1]
    unique_filename = f"{user.id}-{uuid.uuid4().hex}.{ext}"
    file_path = f"{user.id}/{unique_filename}"

    # 4. Upload to Supabase Storage
    supabase_client.storage.from_("profile-pictures").upload(
        path=file_path,
        file=contents,
        file_options={"cache-control": "3600", "upsert": "false"},
    )

    # 5. Delete old profile picture (if exists)
    if user.profile_picture:
        old_path = extract_storage_path(user.profile_picture, "profile-pictures")
        if old_path and old_path.startswith(str(user.id)):
            supabase_client.storage.from_("profile-pictures").remove([old_path])

    # 6. Get public URL
    public_url = supabase_client.storage.from_("profile-pictures").get_public_url(
        file_path
    )

    # 7. Update DB with new URL
    try:
        update_user_profile_picture(db, user_id=user.id, picture_url=public_url)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update profile picture URL in database: {str(e)}",
        )

    return {"profile_picture_url": public_url}


@router.delete("/delete-profile-picture")
async def delete_profile_picture(
    db: SessionDep,
    user=Depends(get_current_profile),
):
    """
    Deletes all profile pictures of the current user from Supabase Storage,
    and sets `profile_picture` to NULL in the `user_profile` table.
    """

    user_folder = str(user.id)

    # 1. List all files in this user's folder inside "profile-pictures" bucket
    try:
        list_res = supabase_client.storage.from_("profile-pictures").list(
            path=user_folder
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list user's profile pictures: {str(e)}",
        )

    # 2. Delete all files found
    if list_res:
        file_paths = [f"{user_folder}/{item['name']}" for item in list_res]
        try:
            supabase_client.storage.from_("profile-pictures").remove(file_paths)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete files from storage: {str(e)}",
            )

    # 3. Update database to set profile_picture = NULL
    try:
        update_user_profile_picture(db, user_id=user.id, picture_url=None)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update profile picture in database: {str(e)}",
        )

    return {"message": "Profile picture deleted successfully."}


# Authenticated: Soft delete my profile
@router.delete("/profile", status_code=status.HTTP_204_NO_CONTENT)
def soft_delete_my_profile(
    db: SessionDep,
    user=Depends(get_current_profile),
):
    db.soft_delete(db, id=user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# Authenticated: Reactivate my profile
@router.post("/profile/reactivate", response_model=UserProfilePublic)
def reactivate_my_account(
    db: SessionDep,
    user=Depends(get_current_profile),
):
    profile = db.reactivate(db, id=user.id)
    return UserProfilePublic.model_validate(profile, from_attributes=True)


# Authenticated: Get my user activity
# @router.get("/activity", response_model=UserActivityPublic)
# async def get_my_activity(user=Depends(get_current_profile), db: SessionDep):
#     """
#     Fetch the current user's activity.
#     """
#     activity = db.get(UserActivity, user.id)
#     if not activity:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="User activity details not found",
#         )
#     return UserActivityPublic.model_validate(activity, from_attributes=True)
