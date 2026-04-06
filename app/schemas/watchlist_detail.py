from typing import List, Optional
from pydantic import BaseModel

from app.schemas.watchlist import WatchlistOut, WatchlistCreate, WatchlistUpdate
from app.schemas.watchlist_item import WatchlistItemBase, WatchlistItemCreateWithoutId


class WatchlistsDetail(BaseModel):
    total: int
    watchlists: List[WatchlistOut]


class WatchlistDetailCreateRequest(BaseModel):
    watchlist_data: WatchlistCreate
    items: Optional[List[WatchlistItemCreateWithoutId]] = None


class WatchlistDetailUpdateRequest(BaseModel):
    watchlist_data: Optional[WatchlistUpdate] = None
    items: Optional[List[WatchlistItemBase]] = None
