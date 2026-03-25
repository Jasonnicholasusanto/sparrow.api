from datetime import date
from typing import Optional
from fastapi import HTTPException, status
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
import uuid
import re


USERNAME_REGEX = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.]*$")


class UserProfileBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    username: str
    full_name: str = Field(min_length=1, max_length=255)
    display_name: Optional[str] = None
    bio: Optional[str] = None
    birth_date: Optional[date] = None
    profile_picture: Optional[str] = None
    background_picture: Optional[str] = None
    phone_number: Optional[str] = Field(default=None, max_length=50)
    email_address: EmailStr = Field(max_length=255)


class UserProfileCreate(UserProfileBase):
    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        if not USERNAME_REGEX.match(v):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username must start with a letter or number and may only contain letters, numbers, underscores, or dots",
            )
        if len(v) < 3 or len(v) > 30:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username must be between 3 and 30 characters",
            )
        return v


class UserProfileUpdateEmail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    email_address: EmailStr = Field(max_length=255)


# Properties to receive on item update
class UserProfileUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    username: Optional[str] = None
    full_name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    display_name: Optional[str] = None
    bio: Optional[str] = None
    birth_date: Optional[date] = None
    phone_number: Optional[str] = Field(default=None, max_length=50)
    is_active: Optional[bool] = None

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if not USERNAME_REGEX.match(v):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username must start with a letter or number and may only contain letters, numbers, underscores, or dots",
            )
        if len(v) < 3 or len(v) > 30:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username must be between 3 and 30 characters",
            )
        return v


class UserProfilePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    auth_id: uuid.UUID
    username: str
    full_name: str
    display_name: Optional[str] = None
    bio: Optional[str] = None
    profile_picture: Optional[str] = None
    background_picture: Optional[str] = None
    created_at: date


class UserProfilesPublic(BaseModel):
    data: list[UserProfilePublic]
    count: int


# Private/me response (richer)
class UserProfileMe(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    auth_id: uuid.UUID
    username: str
    full_name: str
    display_name: Optional[str] = None
    bio: Optional[str] = None
    birth_date: Optional[date] = None
    profile_picture: Optional[str] = None
    background_picture: Optional[str] = None
    phone_number: Optional[str] = None
    email_address: str
    is_active: bool
    is_admin: bool = False
    created_at: date
