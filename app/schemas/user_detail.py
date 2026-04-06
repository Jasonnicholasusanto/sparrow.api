from __future__ import annotations
from typing import List

from pydantic import BaseModel
from app.schemas.user_activity import UserActivityPointsBreakdown, UserActivityPublic
from app.schemas.user_profile import UserProfileMe, UserProfilePublic
from app.schemas.watchlist import UserWatchlistsResponseOut, WatchlistOut


class UserDetailsResponse(BaseModel):
    profile: UserProfileMe
    activity: UserActivityPublic | None
    followers_count: int = 0
    following_count: int = 0
    

class UserDetailsPublic(BaseModel):
    profile: UserProfilePublic
    points: UserActivityPointsBreakdown | None
    followers_count: int = 0
    following_count: int = 0
    watchlists: UserWatchlistsResponseOut | None