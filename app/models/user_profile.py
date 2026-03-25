from datetime import date, datetime, timezone
import uuid
from typing import Optional
from pydantic import EmailStr
from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class UserProfile(SQLModel, table=True):
    """
    Mirrors public.user_profile
    Primary key is id (UUID).
    """

    __tablename__ = "user_profile"
    __table_args__ = {"schema": "public"}

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    auth_id: uuid.UUID = Field(
        index=True,
        unique=True,
        foreign_key="auth.users.id",
        description="FK to auth.users.id",
    )
    username: str = Field(index=True, min_length=1, max_length=50)
    email_address: EmailStr = Field(index=True, max_length=255)
    phone_number: Optional[str] = Field(default=None, max_length=50)
    full_name: str = Field(min_length=1, max_length=255)
    display_name: Optional[str] = None
    bio: Optional[str] = None
    birth_date: Optional[date] = None
    profile_picture: Optional[str] = None
    background_picture: Optional[str] = None
    is_active: bool = Field(default=True)
    is_admin: bool = Field(default=False)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
