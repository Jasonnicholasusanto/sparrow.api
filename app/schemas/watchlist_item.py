from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import ConfigDict, Field
from pydantic import BaseModel


class WatchlistItemBase(BaseModel):
    symbol: str = Field(min_length=1)
    exchange: str = Field(min_length=1)
    note: Optional[str] = Field(default=None, max_length=1000)
    position: Optional[int] = Field(default=None, ge=0)
    quantity: Optional[float] = Field(default=None, ge=0.0)
    reference_price: Optional[float] = Field(default=None, ge=0.0)


class WatchlistItemCreate(WatchlistItemBase):
    watchlist_id: int


class WatchlistItemCreateWithoutId(WatchlistItemBase):
    """Used when watchlist_id is not known yet."""

    pass


class WatchlistItemUpdate(BaseModel):
    symbol: Optional[str] = Field(default=None, min_length=1)
    exchange: Optional[str] = Field(default=None, min_length=1)
    note: Optional[str] = Field(default=None, max_length=1000)
    position: Optional[int] = Field(default=None, ge=0)
    quantity: Optional[float] = Field(default=None, ge=0.0)
    reference_price: Optional[float] = Field(default=None, ge=0.0)


class WatchlistItemTickerDetails(BaseModel):
    last_price: Optional[float] = None
    currency: Optional[str] = None
    previous_close: Optional[float] = None
    volume: Optional[int] = None
    regular_market_change: Optional[float] = None
    regular_market_change_percent: Optional[float] = None


class WatchlistItemOut(WatchlistItemBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    watchlist_id: int
    created_at: datetime
    updated_at: datetime
    ticker_details: Optional[WatchlistItemTickerDetails] = None
