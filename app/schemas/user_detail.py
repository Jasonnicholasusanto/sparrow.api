from __future__ import annotations
from typing import List

from app.schemas.watchlist import WatchlistDetailOut
from pydantic import BaseModel
from app.schemas.user_activity import UserActivityPointsBreakdown, UserActivityPublic
from app.schemas.user_profile import UserProfileMe, UserProfilePublic


class UserDetailsResponse(BaseModel):
    profile: UserProfileMe
    activity: UserActivityPublic | None
    followers_count: int = 0
    following_count: int = 0


class WatchlistSummary(BaseModel):
    total: int
    watchlists: List[WatchlistDetailOut] | None

class UserDetailsPublic(BaseModel):
    profile: UserProfilePublic
    points: UserActivityPointsBreakdown | None
    followers_count: int = 0
    following_count: int = 0
    watchlists: WatchlistSummary