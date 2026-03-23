from uuid import UUID
from app.services.watchlist_service import get_user_public_watchlists
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.dependencies.profile import get_current_profile
from app.api.deps import SessionDep
from app.schemas.user_activity import UserActivityPointsBreakdown
from app.schemas.user_detail import UserDetailsPublic
from app.schemas.user_follow import PaginatedFollowersResponse
from app.schemas.user_profile import (
    USERNAME_REGEX,
    UserProfilePublic,
    UserProfilesPublic,
)
from app.services.user_activity_service import get_user_points
from app.services.user_follow_service import (
    get_followers,
    get_followers_count,
    get_following,
    get_following_count,
)
from app.services.user_profile_service import (
    _username_exists,
    get_user_profile_by_username,
    list_user_profiles,
)


router = APIRouter(prefix="/users", tags=["users"])


# Public: Get a profile by username
@router.get("/@{username}", response_model=UserDetailsPublic)
def get_public_user_profile_by_username(
    username: str,
    db: SessionDep,
    user=Depends(get_current_profile),
):
    """
    Public profile lookup by username (case-insensitive).
    Returns 404 if not found or if the profile is deactivated.
    """
    if not username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Username is required."
        )

    profile = get_user_profile_by_username(db, username=username)

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found."
        )

    points = get_user_points(db, profile_id=profile.id)

    # 3) Followers and Following counts
    followers_count = get_followers_count(db, user_id=profile.id)
    following_count = get_following_count(db, user_id=profile.id)

    # 4) Watchlists
    public_watchlists = get_user_public_watchlists(db, user_profile_id=profile.id)
    print("Public watchlists:", public_watchlists)
    watchlists = {
        "total": len(public_watchlists),
        "watchlists": public_watchlists,
    }

    return UserDetailsPublic(
        profile=UserProfilePublic.model_validate(profile, from_attributes=True),
        points=UserActivityPointsBreakdown.model_validate(points, from_attributes=True)
        if points
        else None,
        followers_count=followers_count or 0,
        following_count=following_count or 0,
        watchlists=watchlists,
    )


@router.get("/search", response_model=UserProfilesPublic)
def search_users(
    q: str = Query(..., min_length=1, max_length=64),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: SessionDep = None,
    user=Depends(get_current_profile),
):
    if not q:
        raise HTTPException(status_code=400, detail="Query parameter 'q' is required.")

    return list_user_profiles(
        db,
        skip=offset,
        limit=limit,
        q=q,
        only_active=True,
    )


@router.get("/check-username")
def check_username(
    username: str,
    db: SessionDep = None,
):
    """
    Returns {'available': bool}. Case-insensitive check against user_profile.username.
    """
    if not username:
        raise HTTPException(status_code=400, detail="Username is required.")

    if not USERNAME_REGEX.match(username):
        raise HTTPException(
            status_code=400,
            detail="Invalid username. Must start with a letter or number and may only contain letters, numbers, underscores, or dots",
        )
    if len(username) < 3 or len(username) > 30:
        raise HTTPException(
            status_code=400,
            detail="Invalid username length. Must be between 3 and 30 characters.",
        )

    exists = _username_exists(session=db, username=username)
    return {"available": not exists}


@router.get("/{user_id}/followers", response_model=PaginatedFollowersResponse)
def list_followers(
    user_id: UUID,
    db: SessionDep = None,
    limit: int = 20,
    offset: int = 0,
    user=Depends(get_current_profile),
):
    """
    Returns list of users who follow the given user.
    """
    total = get_followers_count(db, user_id)
    followers = get_followers(db, user_id, limit=limit, offset=offset)

    return PaginatedFollowersResponse(
        total=total,
        limit=limit,
        offset=offset,
        data=[
            UserProfilePublic.model_validate(u, from_attributes=True) for u in followers
        ],
    )


@router.get("/{user_id}/following", response_model=PaginatedFollowersResponse)
def list_following(
    user_id: UUID,
    db: SessionDep = None,
    limit: int = 20,
    offset: int = 0,
    user=Depends(get_current_profile),
):
    """
    Returns list of users the given user is following.
    """
    total = get_following_count(db, user_id)
    following = get_following(db, user_id, limit=limit, offset=offset)
    return PaginatedFollowersResponse(
        total=total,
        limit=limit,
        offset=offset,
        data=[
            UserProfilePublic.model_validate(u, from_attributes=True) for u in following
        ],
    )
