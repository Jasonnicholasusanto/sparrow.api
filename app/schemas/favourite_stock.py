from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict

from app.schemas.stocks import TickerMarketSnapshotResponse


class FavouriteStockBase(BaseModel):
    symbol: str
    exchange: str
    note: Optional[str] = None
    name: Optional[str] = None


class FavouriteStockOut(FavouriteStockBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    created_at: datetime
    updated_at: datetime
    ticker_details: Optional[TickerMarketSnapshotResponse] = None


class FavouriteStockCreate(FavouriteStockBase):
    pass


class FavouriteStockUpdate(BaseModel):
    note: Optional[str] = None