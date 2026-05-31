from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class WatchlistAuditEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    watchlist_id: Optional[int] = None
    user_profile_id: UUID
    action: str
    item_id: Optional[int] = None
    before_data: Optional[dict[str, Any]] = None
    after_data: Optional[dict[str, Any]] = None
    meta_data: Optional[dict[str, Any]] = None
    created_at: datetime