from typing import List, Optional
from pydantic import BaseModel

from app.schemas.watchlist import WatchlistOut, WatchlistCreate
from app.schemas.watchlist_item import WatchlistItemCreateWithoutId


class WatchlistsDetail(BaseModel):
    total: int
    watchlists: List[WatchlistOut]


class WatchlistDetailCreateRequest(BaseModel):
    watchlist_data: WatchlistCreate
    items: Optional[List[WatchlistItemCreateWithoutId]] = None
