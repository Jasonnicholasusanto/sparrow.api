from typing import Iterable, Optional
import uuid
from sqlmodel import Session, func, select
from app.crud.user_profile import user_profile as user_profile_crud
from app.models.auth import Identity
from app.models.user_profile import UserProfile
from app.schemas.user_profile import (
    UserProfileCreate,
    UserProfileUpdate,
    UserProfilePublic,
    UserProfileUpdateEmail,
    UserProfilesPublic,
    UserProfileMe,
)


def _username_exists(
    session: Session, username: str, exclude_id: Optional[uuid.UUID] = None
) -> bool:
    stmt = select(UserProfile.id).where(UserProfile.username == username)
    if exclude_id:
        stmt = stmt.where(UserProfile.id != exclude_id)
    stmt = stmt.limit(1)
    return session.exec(stmt).first() is not None


def _email_exists(
    session: Session, email: str, exclude_id: Optional[uuid.UUID] = None
) -> bool:
    stmt = select(UserProfile.id).where(UserProfile.email_address == email)
    if exclude_id:
        stmt = stmt.where(UserProfile.id != exclude_id)
    stmt = stmt.limit(1)
    return session.exec(stmt).first() is not None


def _email_exists_auth_identity(
    session: Session, email: str, exclude_id: Optional[uuid.UUID] = None
) -> bool:
    stmt = select(Identity.id).where(Identity.email == email)
    if exclude_id:
        stmt = stmt.where(Identity.user_id != exclude_id)
    stmt = stmt.limit(1)
    return session.exec(stmt).first() is not None


# ---------------------------------------------------------------------------------------------------------------------
# Create User Profile
# ---------------------------------------------------------------------------------------------------------------------


def create_user_profile(
    session: Session,
    *,
    auth_id: uuid.UUID,
    profile_in: UserProfileCreate,
) -> UserProfileMe:
    """
    Create a new profile bound to auth_id. Enforces username/email uniqueness.
    """
    if _username_exists(session, profile_in.username):
        raise ValueError("Username is already taken.")
    if _email_exists(session, str(profile_in.email_address)):
        raise ValueError("Email address is already in use.")

    db_obj = user_profile_crud.create(session, obj_in=profile_in, auth_id=auth_id)

    if db_obj:
        db_obj.created_at = db_obj.created_at.date()

    return UserProfileMe.model_validate(db_obj)


# ---------------------------------------------------------------------------------------------------------------------
# Read User Profile
# ---------------------------------------------------------------------------------------------------------------------


def get_user_profile(
    session: Session, *, user_id: uuid.UUID
) -> Optional[UserProfilePublic]:
    obj = user_profile_crud.get(session, id=user_id)
    if obj:
        obj.created_at = obj.created_at.date()
    return UserProfilePublic.model_validate(obj) if obj else None


def get_user_profile_db(
    session: Session, *, user_id: uuid.UUID
) -> Optional[UserProfile]:
    """Raw DB object (useful internally for chaining logic)."""
    return user_profile_crud.get(session, id=user_id)


def get_user_profile_by_auth(
    session: Session, *, auth_id: uuid.UUID
) -> Optional[UserProfileMe]:
    obj = user_profile_crud.get_by_auth_id(session, auth_id=auth_id)
    if obj:
        obj.created_at = obj.created_at.date()
    return UserProfileMe.model_validate(obj) if obj else None


def get_user_profile_by_username(
    session: Session, *, username: str
) -> Optional[UserProfilePublic]:
    obj = user_profile_crud.get_by_username(session, username=username)
    if obj:
        obj.created_at = obj.created_at.date()
    return UserProfilePublic.model_validate(obj) if obj else None


# ---------------------------------------------------------------------------------------------------------------------
# List User Profiles
# ---------------------------------------------------------------------------------------------------------------------


def list_user_profiles(
    session: Session,
    *,
    skip: int = 0,
    limit: int = 50,
    q: Optional[str] = None,
    only_active: bool = True,
) -> UserProfilesPublic:
    """
    List profiles with optional fuzzy search across username/full_name/display_name/email.
    """
    stmt = select(UserProfile)

    if only_active:
        stmt = stmt.where(UserProfile.is_active.is_(True))

    if q:
        # basic ILIKE search over a few fields
        like = f"%{q}%"
        stmt = stmt.where(
            (UserProfile.username.ilike(like))
            | (UserProfile.full_name.ilike(like))
            | (UserProfile.display_name.ilike(like))
            | (UserProfile.email_address.ilike(like))
        )

    count_stmt = stmt.with_only_columns(func.count(UserProfile.id))
    total = session.exec(count_stmt).one()

    stmt = stmt.order_by(UserProfile.username).offset(skip).limit(limit)
    rows: Iterable[UserProfile] = session.exec(stmt).all()  # type: ignore

    for r in rows:
        r.created_at = r.created_at.date()

    data = [UserProfilePublic.model_validate(r) for r in rows]
    return UserProfilesPublic(data=data, count=total)


# ---------------------------------------------------------------------------------------------------------------------
# Update User Profile
# ---------------------------------------------------------------------------------------------------------------------


def update_user_profile(
    session: Session,
    *,
    user_id: uuid.UUID,
    profile_update: UserProfileUpdate,
) -> Optional[UserProfileMe]:
    """
    Patch update. Prevents changing auth_id and enforces uniqueness on username/email if present.
    """
    existing = user_profile_crud.get(session, id=user_id)
    if not existing:
        return None

    if profile_update.username and _username_exists(
        session, profile_update.username, exclude_id=user_id
    ):
        raise ValueError("Username is already taken.")

    # Explicitly guard against accidental auth_id changes if someone slips it into the payload
    if hasattr(profile_update, "auth_id"):
        raise ValueError("auth_id cannot be modified.")

    updated = user_profile_crud.update(session, id=user_id, obj_in=profile_update)
    if updated:
        updated.created_at = updated.created_at.date()
    return UserProfileMe.model_validate(updated) if updated else None


def update_user_email_address(
    session: Session,
    *,
    user_id: uuid.UUID,
    email_update: UserProfileUpdateEmail,
) -> Optional[UserProfileMe]:
    """
    Update user email address with uniqueness check.
    """
    existing = user_profile_crud.get(session, id=user_id)
    if not existing:
        return None

    updated = user_profile_crud.update(session, id=user_id, obj_in=email_update)

    if updated:
        updated.created_at = updated.created_at.date()

    return UserProfileMe.model_validate(updated) if updated else None


# ---------------------------------------------------------------------------------------------------------------------
# Delete / Reactivate User Profile
# ---------------------------------------------------------------------------------------------------------------------


def soft_delete_user_profile(
    session: Session, *, user_id: uuid.UUID
) -> Optional[UserProfileMe]:
    obj = user_profile_crud.soft_delete(session, id=user_id)
    if obj:
        obj.created_at = obj.created_at.date()
    return UserProfileMe.model_validate(obj) if obj else None


def reactivate_user_profile(
    session: Session, *, user_id: uuid.UUID
) -> Optional[UserProfileMe]:
    obj = user_profile_crud.reactivate(session, id=user_id)
    if obj:
        obj.created_at = obj.created_at.date()
    return UserProfileMe.model_validate(obj) if obj else None


# ---------------------------------------------------------------------------------------------------------------------
# Get me convenience
# ---------------------------------------------------------------------------------------------------------------------


def get_me(session: Session, *, auth_id: uuid.UUID) -> Optional[UserProfileMe]:
    """
    Convenience: return the richer 'me' payload for the authenticated user.
    """
    obj = user_profile_crud.get_by_auth_id(session, auth_id=auth_id)
    if obj:
        obj.created_at = obj.created_at.date()
    return UserProfileMe.model_validate(obj) if obj else None


# ---------------------------------------------------------------------------------------------------------------------
# Profile Picture Upload Handling
# ---------------------------------------------------------------------------------------------------------------------


def update_user_profile_picture(
    db: Session, *, user_id: uuid.UUID, picture_url: str
) -> None:
    """
    Update the profile picture for the given user in Postgres.
    """
    profile = db.exec(select(UserProfile).where(UserProfile.id == user_id)).first()
    if not profile:
        return None

    profile.profile_picture = picture_url
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


def update_user_background_picture(
    db: Session, *, user_id: uuid.UUID, background_url: str
) -> None:
    """
    Update the background picture for the given user in Postgres.
    """
    profile = db.exec(select(UserProfile).where(UserProfile.id == user_id)).first()
    if not profile:
        return None

    profile.background_picture = background_url
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile
