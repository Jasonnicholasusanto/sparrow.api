from __future__ import annotations
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Union
import uuid
from fastapi import HTTPException, status
from sqlmodel import Session, select
from app.crud.watchlist_item import watchlist_item as watchlist_item_crud
from app.crud.watchlist import watchlist as watchlist_crud
from app.crud.watchlist_share import watchlist_share as watchlist_share_crud
from app.crud.watchlist_bookmark import watchlist_bookmark as watchlist_bookmark_crud
from app.models.watchlist import Watchlist
from app.models.watchlist_bookmark import WatchlistBookmark
from app.models.watchlist_item import WatchlistItem
from app.models.watchlist_share import WatchlistShare
from app.schemas.stocks import TickerFastInfoResponse, TickersRequest
from app.schemas.watchlist import (
    StockAllocationType,
    UserWatchlistsGroupedResultsOut,
    WatchlistCreate,
    WatchlistDetailOut,
    WatchlistForkOut,
    WatchlistOut,
    WatchlistUpdate,
    WatchlistVisibility,
)
from app.schemas.watchlist_bookmark import WatchlistBookmarkBase
from app.schemas.watchlist_item import (
    WatchlistItemBase,
    WatchlistItemCreate,
    WatchlistItemCreateWithoutId,
    WatchlistItemOut,
    WatchlistItemUpdate,
)
from app.schemas.watchlist_share import WatchlistShareCreate
import yfinance as yf

from app.services.yfinance_service import fetch_ticker_market_snapshots
from app.utils.global_variables import WATCHLIST_GROUP_KEYS


def search_public_watchlists_by_name(
    session: Session, *, name: str, limit: int = 20, offset: int = 0
):
    return watchlist_crud.list_public_by_name(
        session, name=name, limit=limit, offset=offset
    )

def get_user_public_watchlists(
    session,
    *,
    user_profile_id: uuid.UUID,
    limit: int = 20,
    offset: int = 0,
) -> list[WatchlistDetailOut]:
    watchlists_stmt = (
        select(Watchlist)
        .where(
            Watchlist.user_id == user_profile_id,
            Watchlist.visibility == WatchlistVisibility.PUBLIC,
        )
        .order_by(Watchlist.created_at.desc())
        .offset(offset)
        .limit(limit)
    )

    watchlists = list(session.exec(watchlists_stmt).all())

    if not watchlists:
        return []

    watchlist_ids = [watchlist.id for watchlist in watchlists]

    items_stmt = (
        select(WatchlistItem)
        .where(WatchlistItem.watchlist_id.in_(watchlist_ids))
        .order_by(WatchlistItem.watchlist_id, WatchlistItem.position.asc(), WatchlistItem.id.asc())
    )

    items = list(session.exec(items_stmt).all())

    items_by_watchlist_id: dict[int, list[WatchlistItem]] = defaultdict(list)
    for item in items:
        items_by_watchlist_id[item.watchlist_id].append(item)

    return [
        WatchlistDetailOut(
            watchlist=WatchlistOut.model_validate(watchlist, from_attributes=True),
            items=[WatchlistItemBase.model_validate(item, from_attributes=True) for item in items_by_watchlist_id.get(watchlist.id, [])],
        )
        for watchlist in watchlists
    ]

# def get_all_user_related_watchlists(
#     session,
#     *,
#     user_profile_id: uuid.UUID,
#     limit: int = 50,
#     offset: int = 0,
# ) -> dict:
#     """
#     Fetch all watchlists associated with a user, including:
#       1. Watchlists the user created (originals),
#       2. Watchlists the user forked from others,
#       3. Watchlists shared with the user,
#       4. Watchlists the user bookmarked.

#     Also attaches watchlist_items for each returned watchlist.
#     """

#     # 1. Watchlists CREATED by the user (excluding forks)
#     owned_stmt = (
#         select(Watchlist)
#         .where(
#             Watchlist.user_id == user_profile_id,
#             Watchlist.forked_from_id.is_(None),
#         )
#         .order_by(Watchlist.created_at.desc())
#     )
#     owned_watchlists = list(session.exec(owned_stmt).all())

#     # 2. Watchlists FORKED by the user
#     forked_stmt = (
#         select(Watchlist)
#         .where(
#             Watchlist.user_id == user_profile_id,
#             Watchlist.forked_from_id.is_not(None),
#         )
#         .order_by(Watchlist.created_at.desc())
#     )
#     forked_watchlists = list(session.exec(forked_stmt).all())

#     # 3. Watchlists SHARED with the user
#     shared_stmt = (
#         select(Watchlist)
#         .join(WatchlistShare, WatchlistShare.watchlist_id == Watchlist.id)
#         .where(WatchlistShare.user_id == user_profile_id)
#         .order_by(Watchlist.created_at.desc())
#     )
#     shared_watchlists = list(session.exec(shared_stmt).all())

#     # 4. Watchlists BOOKMARKED by the user
#     bookmarked_stmt = (
#         select(Watchlist)
#         .join(WatchlistBookmark, WatchlistBookmark.watchlist_id == Watchlist.id)
#         .where(WatchlistBookmark.user_id == user_profile_id)
#         .order_by(Watchlist.created_at.desc())
#     )
#     bookmarked_watchlists = list(session.exec(bookmarked_stmt).all())

#     # Apply pagination to each subset
#     if limit:
#         owned_watchlists = owned_watchlists[offset : offset + limit]
#         forked_watchlists = forked_watchlists[offset : offset + limit]
#         shared_watchlists = shared_watchlists[offset : offset + limit]
#         bookmarked_watchlists = bookmarked_watchlists[offset : offset + limit]

#     # Collect all unique watchlist IDs from all categories
#     all_watchlists = (
#         owned_watchlists
#         + forked_watchlists
#         + shared_watchlists
#         + bookmarked_watchlists
#     )

#     watchlist_ids = list({w.id for w in all_watchlists})

#     # Fetch all items in one query
#     items_by_watchlist_id: dict[int, list[WatchlistItem]] = defaultdict(list)

#     if watchlist_ids:
#         items_stmt = (
#             select(WatchlistItem)
#             .where(WatchlistItem.watchlist_id.in_(watchlist_ids))
#             .order_by(
#                 WatchlistItem.watchlist_id,
#                 WatchlistItem.position.asc(),
#                 WatchlistItem.id.asc(),
#             )
#         )

#         items = list(session.exec(items_stmt).all())

#         for item in items:
#             items_by_watchlist_id[item.watchlist_id].append(item)

#     def build_watchlist_out(w: Watchlist) -> WatchlistOut:
#         base = WatchlistOut.model_validate(w, from_attributes=True).model_dump()

#         base["items"] = [
#             WatchlistItemOut.model_validate(item, from_attributes=True)
#             for item in items_by_watchlist_id.get(w.id, [])
#         ]

#         return WatchlistOut(**base)

#     return {
#         "created": [build_watchlist_out(w) for w in owned_watchlists],
#         "forked": [build_watchlist_out(w) for w in forked_watchlists],
#         "shared": [build_watchlist_out(w) for w in shared_watchlists],
#         "bookmarked": [build_watchlist_out(w) for w in bookmarked_watchlists],
#         "total_count": len(owned_watchlists)
#         + len(forked_watchlists)
#         + len(shared_watchlists)
#         + len(bookmarked_watchlists),
#         "counts": {
#             "owned": len(owned_watchlists),
#             "forked": len(forked_watchlists),
#             "shared": len(shared_watchlists),
#             "bookmarked": len(bookmarked_watchlists),
#         },
#     }

def get_all_user_related_watchlists(
    session,
    *,
    user_profile_id: uuid.UUID,
    limit: int = 50,
    offset: int = 0,
    is_public_only: bool = False,
) -> UserWatchlistsGroupedResultsOut:
    """
    Fetch all watchlists associated with a user, including:
      1. Watchlists the user created (originals),
      2. Watchlists the user forked from others,
      3. Watchlists shared with the user,
      4. Watchlists the user bookmarked.

    If is_public_only is True, only PUBLIC watchlists are returned.
    Also attaches watchlist_items for each returned watchlist.
    """

    def apply_visibility_filters(stmt):
        if is_public_only:
            stmt = stmt.where(Watchlist.visibility == "public")
        return stmt

    # 1. Watchlists CREATED by the user (excluding forks)
    owned_stmt = (
        select(Watchlist)
        .where(
            Watchlist.user_id == user_profile_id,
            Watchlist.forked_from_id.is_(None),
        )
        .order_by(Watchlist.created_at.desc())
    )
    owned_stmt = apply_visibility_filters(owned_stmt)
    owned_watchlists = list(session.exec(owned_stmt).all())

    # 2. Watchlists FORKED by the user
    forked_stmt = (
        select(Watchlist)
        .where(
            Watchlist.user_id == user_profile_id,
            Watchlist.forked_from_id.is_not(None),
        )
        .order_by(Watchlist.created_at.desc())
    )
    forked_stmt = apply_visibility_filters(forked_stmt)
    forked_watchlists = list(session.exec(forked_stmt).all())

    # 3. Watchlists SHARED with the user
    shared_stmt = (
        select(Watchlist)
        .join(WatchlistShare, WatchlistShare.watchlist_id == Watchlist.id)
        .where(WatchlistShare.user_id == user_profile_id)
        .order_by(Watchlist.created_at.desc())
    )
    shared_stmt = apply_visibility_filters(shared_stmt)
    shared_watchlists = list(session.exec(shared_stmt).all())

    # 4. Watchlists BOOKMARKED by the user
    bookmarked_stmt = (
        select(Watchlist)
        .join(WatchlistBookmark, WatchlistBookmark.watchlist_id == Watchlist.id)
        .where(WatchlistBookmark.user_id == user_profile_id)
        .order_by(Watchlist.created_at.desc())
    )
    bookmarked_stmt = apply_visibility_filters(bookmarked_stmt)
    bookmarked_watchlists = list(session.exec(bookmarked_stmt).all())

    # Apply pagination to each subset
    if limit:
        owned_watchlists = owned_watchlists[offset : offset + limit]
        forked_watchlists = forked_watchlists[offset : offset + limit]
        shared_watchlists = shared_watchlists[offset : offset + limit]
        bookmarked_watchlists = bookmarked_watchlists[offset : offset + limit]

    # Collect all unique watchlist IDs from all categories
    all_watchlists = (
        owned_watchlists
        + forked_watchlists
        + shared_watchlists
        + bookmarked_watchlists
    )

    watchlist_ids = list({w.id for w in all_watchlists})

    # Fetch all items in one query
    items_by_watchlist_id: dict[int, list[WatchlistItem]] = defaultdict(list)

    if watchlist_ids:
        items_stmt = (
            select(WatchlistItem)
            .where(WatchlistItem.watchlist_id.in_(watchlist_ids))
            .order_by(
                WatchlistItem.watchlist_id,
                WatchlistItem.position.asc(),
                WatchlistItem.id.asc(),
            )
        )

        items = list(session.exec(items_stmt).all())

        for item in items:
            items_by_watchlist_id[item.watchlist_id].append(item)

    def build_watchlist_out(w: Watchlist) -> WatchlistOut:
        watchlist_out = WatchlistOut.model_validate(w, from_attributes=True)

        items = [
            WatchlistItemOut.model_validate(item, from_attributes=True)
            for item in items_by_watchlist_id.get(w.id, [])
        ]

        return watchlist_out.model_copy(update={"items": items})
    
    created_results = [build_watchlist_out(w) for w in owned_watchlists]
    forked_results = [build_watchlist_out(w) for w in forked_watchlists]
    shared_results = [build_watchlist_out(w) for w in shared_watchlists]
    bookmarked_results = [build_watchlist_out(w) for w in bookmarked_watchlists]

    return UserWatchlistsGroupedResultsOut(
        created=created_results,
        forked=forked_results,
        shared=shared_results,
        bookmarked=bookmarked_results,
        total_count=len(created_results)
        + len(forked_results)
        + len(shared_results)
        + len(bookmarked_results),
        counts={
            "owned": len(created_results),
            "forked": len(forked_results),
            "shared": len(shared_results),
            "bookmarked": len(bookmarked_results),
        },
    )

# def enrich_user_watchlists_with_market_snapshots(user_watchlists: UserWatchlistsGroupedResultsOut) -> dict:
#     symbols = [
#         item.symbol
#         for key in WATCHLIST_GROUP_KEYS
#         for watchlist in user_watchlists.get(key, [])
#         for item in watchlist.items
#         if item.symbol
#     ]

#     snapshot_map = fetch_ticker_market_snapshots(symbols)

#     return {
#         "created": [
#             {
#                 **watchlist.model_dump(),
#                 "items": [
#                     {
#                         **item.model_dump(),
#                         "tickerDetails": snapshot_map.get((item.symbol or "").upper()),
#                     }
#                     for item in watchlist.items
#                 ],
#             }
#             for watchlist in user_watchlists.get("created", [])
#         ],
#         "forked": [
#             {
#                 **watchlist.model_dump(),
#                 "items": [
#                     {
#                         **item.model_dump(),
#                         "tickerDetails": snapshot_map.get((item.symbol or "").upper()),
#                     }
#                     for item in watchlist.items
#                 ],
#             }
#             for watchlist in user_watchlists.get("forked", [])
#         ],
#         "shared": [
#             {
#                 **watchlist.model_dump(),
#                 "items": [
#                     {
#                         **item.model_dump(),
#                         "tickerDetails": snapshot_map.get((item.symbol or "").upper()),
#                     }
#                     for item in watchlist.items
#                 ],
#             }
#             for watchlist in user_watchlists.get("shared", [])
#         ],
#         "bookmarked": [
#             {
#                 **watchlist.model_dump(),
#                 "items": [
#                     {
#                         **item.model_dump(),
#                         "tickerDetails": snapshot_map.get((item.symbol or "").upper()),
#                     }
#                     for item in watchlist.items
#                 ],
#             }
#             for watchlist in user_watchlists.get("bookmarked", [])
#         ],
#         "total_count": user_watchlists.get("total_count", 0),
#         "counts": user_watchlists.get("counts", {}),
#     }

def enrich_user_watchlists_with_market_snapshots(
    user_watchlists: UserWatchlistsGroupedResultsOut,
) -> UserWatchlistsGroupedResultsOut:
    symbols = [
        item.symbol
        for key in WATCHLIST_GROUP_KEYS
        for watchlist in getattr(user_watchlists, key, [])
        for item in (watchlist.items or [])
        if item.symbol
    ]

    snapshot_map = fetch_ticker_market_snapshots(symbols)

    def enrich_watchlists(watchlists: list[WatchlistOut]) -> list[WatchlistOut]:
        enriched_watchlists: list[WatchlistOut] = []

        for watchlist in watchlists:
            enriched_items = [
                WatchlistItemOut(
                    **item.model_dump(exclude={"ticker_details"}),
                    ticker_details=snapshot_map.get((item.symbol or "").upper()),
                )
                for item in (watchlist.items or [])
            ]

            enriched_watchlists.append(
                WatchlistOut(
                    **watchlist.model_dump(exclude={"items"}),
                    items=enriched_items,
                )
            )

        return enriched_watchlists

    return UserWatchlistsGroupedResultsOut(
        created=enrich_watchlists(user_watchlists.created),
        forked=enrich_watchlists(user_watchlists.forked),
        shared=enrich_watchlists(user_watchlists.shared),
        bookmarked=enrich_watchlists(user_watchlists.bookmarked),
        total_count=user_watchlists.total_count,
        counts=user_watchlists.counts,
    )

def enrich_user_watchlists_with_fast_info(user_watchlists: dict) -> dict:
    symbols: list[str] = []

    for group_key in WATCHLIST_GROUP_KEYS:
        watchlists = user_watchlists.get(group_key, [])
        for watchlist in watchlists:
            for item in watchlist.items:
                if item.symbol:
                    symbols.append(item.symbol)

    ticker_map = fetch_tickers_fast_info(symbols)

    enriched = {
        "created": [],
        "forked": [],
        "shared": [],
        "bookmarked": [],
        "total_count": user_watchlists.get("total_count", 0),
        "counts": user_watchlists.get("counts", {}),
    }

    for group_key in WATCHLIST_GROUP_KEYS:
        watchlists = user_watchlists.get(group_key, [])

        for watchlist in watchlists:
            watchlist_data = watchlist.model_dump()

            enriched_items = []
            for item in watchlist.items:
                item_data = item.model_dump()
                symbol = (item.symbol or "").upper()
                item_data["fast_info"] = ticker_map.get(symbol)
                enriched_items.append(item_data)

            watchlist_data["items"] = enriched_items
            enriched[group_key].append(watchlist_data)

    return enriched

def fetch_tickers_fast_info(symbols: TickersRequest) -> dict[str, Any]:
    if not symbols:
        return {}

    normalized_symbols = [
        symbol.strip().upper()
        for symbol in symbols
        if symbol and symbol.strip()
    ]

    if not normalized_symbols:
        return {}

    try:
        tickers_data = yf.Tickers(" ".join(normalized_symbols))
        results: dict[str, Any] = {}

        for symbol in normalized_symbols:
            try:
                ticker = tickers_data.tickers.get(symbol)
                if not ticker:
                    results[symbol] = {"error": f"Ticker '{symbol}' not found"}
                    continue

                fi = dict(ticker.fast_info or {})
                results[symbol] = TickerFastInfoResponse(
                    symbol=symbol,
                    **fi,
                )
            except Exception as inner_e:
                results[symbol] = {"error": str(inner_e)}

        return results

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch ticker fast info: {str(e)}",
        )


def get_watchlists_shared_with_user(
    session,
    *,
    user_profile_id: uuid.UUID,
    limit: int = 20,
    offset: int = 0,
) -> List[WatchlistOut]:
    """
    Fetch all watchlists that have been shared with a specific user.
    Includes whether the user has edit permissions.
    """
    stmt = (
        select(Watchlist, WatchlistShare.can_edit)
        .join(WatchlistShare, WatchlistShare.watchlist_id == Watchlist.id)
        .where(WatchlistShare.user_id == user_profile_id)
        .order_by(Watchlist.created_at.desc())
        .limit(limit)
        .offset(offset)
    )

    results = session.exec(stmt).all()

    watchlists = []
    for w, can_edit in results:
        watchlist_out = WatchlistOut.model_validate(w, from_attributes=True)
        watchlist_out_dict = watchlist_out.model_dump()
        watchlist_out_dict["can_edit"] = can_edit
        watchlists.append(watchlist_out_dict)

    return watchlists


def watchlist_item_exists(
    session, *, watchlist_id: int, symbol: str, exchange: str
) -> bool:
    """
    Returns True if the given symbol already exists in the watchlist.
    """
    stmt = select(WatchlistItem).where(
        (WatchlistItem.watchlist_id == watchlist_id)
        & (WatchlistItem.symbol == symbol)
        & (WatchlistItem.exchange == exchange)
    )
    existing = session.exec(stmt).first()
    return existing is not None


def load_items_for_watchlists(
    session: Session, watchlist_ids: List[int]
) -> Dict[int, List[WatchlistItem]]:
    """Batch load items for many watchlists to avoid N+1."""
    if not watchlist_ids:
        return {}
    stmt = (
        select(WatchlistItem)
        .where(WatchlistItem.watchlist_id.in_(watchlist_ids))
        .order_by(
            WatchlistItem.watchlist_id.asc(),
            WatchlistItem.position.asc().nulls_last(),
            WatchlistItem.created_at.asc(),
        )
    )
    items_by_wl: Dict[int, list[WatchlistItem]] = {}
    for it in session.exec(stmt).all():
        items_by_wl.setdefault(it.watchlist_id, []).append(it)
    return items_by_wl


def get_watchlist_items_securely(
    session: Session,
    *,
    watchlist_id: int,
    user_profile_id: uuid.UUID,
) -> list[WatchlistItem]:
    """
    Return items for a watchlist if the user has permission to view it.

    Access rules:
      1. User owns the watchlist, OR
      2. The watchlist is shared with the user, OR
      3. The watchlist is public
    """
    # 1) Get the watchlist
    watchlist = watchlist_crud.get(session, id=watchlist_id)
    if not watchlist:
        raise HTTPException(status_code=404, detail="Watchlist not found.")

    # 2) Evaluate access with minimal queries
    is_owner = watchlist.user_id == user_profile_id
    is_public = watchlist.visibility == WatchlistVisibility.PUBLIC.value

    has_share = False
    if not (is_owner or is_public):
        # Only query shares if owner/public checks failed
        has_share = bool(
            watchlist_share_crud.get_share(
                session=session,
                watchlist_id=watchlist_id,
                user_id=user_profile_id,
            )
        )

    if not (is_owner or is_public or has_share):
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to view this watchlist's items.",
        )

    # 3) Fetch items after passing all checks
    return watchlist_item_crud.list_by_watchlist_id(
        session=session,
        watchlist_id=watchlist_id,
    )


def user_can_edit_watchlist(
    session: Session, user_id: uuid.UUID, watchlist_id: int
) -> bool:
    """
    Checks if the given user can edit the specified watchlist.

    A user can edit if:
    1. They own the watchlist (watchlist.user_id == user_id), or
    2. The watchlist is shared with them and can_edit = True.
    """

    # 1. Check if user owns the watchlist
    watchlist = session.exec(
        select(Watchlist).where(Watchlist.id == watchlist_id)
    ).first()
    if not watchlist:
        return False

    if watchlist.user_id == user_id:
        return True

    # 2. Otherwise check shared permissions
    shared_access = session.exec(
        select(WatchlistShare).where(
            (WatchlistShare.watchlist_id == watchlist_id)
            & (WatchlistShare.user_id == user_id)
            & (WatchlistShare.can_edit)
        )
    ).first()

    return shared_access is not None


def create_watchlist_for_user(
    session: Session,
    *,
    user_id: uuid.UUID,
    watchlist_data: WatchlistCreate,
) -> WatchlistOut:
    """
    Create a new watchlist for the given user.
    """
    db_obj = watchlist_crud.create(session, owner_id=user_id, obj_in=watchlist_data)
    return WatchlistOut.model_validate(db_obj, from_attributes=True)


def add_item_to_watchlist(
    session: Session,
    *,
    user_profile_id: uuid.UUID,
    item: WatchlistItemCreate,
) -> WatchlistItem:
    """
    Add a new item to the specified watchlist.
    Uses CRUDWatchlistItem.create() for persistence.
    """
    # 1. Validate edit permissions
    user_access = user_can_edit_watchlist(
        session=session,
        watchlist_id=item.watchlist_id,
        user_id=user_profile_id,
    )

    if not user_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to edit this watchlist.",
        )

    # 2. Prevent duplicate entries
    if watchlist_item_exists(
        session=session,
        watchlist_id=item.watchlist_id,
        symbol=item.symbol,
        exchange=item.exchange,
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Symbol '{item.symbol}' already exists in this watchlist.",
        )

    # 3. Create the item
    item_in = WatchlistItemCreate(
        symbol=item.symbol,
        exchange=item.exchange,
        note=item.note,
        position=item.position,
        watchlist_id=item.watchlist_id,
    )

    return watchlist_item_crud.create(
        session=session,
        watchlist_id=item.watchlist_id,
        obj_in=item_in,
    )


def add_many_items_to_watchlist(
    session: Session,
    *,
    watchlist_id: int,
    items: Iterable[Union[WatchlistItemCreate, WatchlistItemCreateWithoutId]],
) -> List[WatchlistItemBase]:
    """
    Add multiple items to the specified watchlist.
    Uses CRUDWatchlistItem.create_many() for persistence.
    """
    if not items:
        return []

    normalized_items = [
        WatchlistItemCreate(
            watchlist_id=watchlist_id,
            **{k: v for k, v in item.model_dump().items() if k != "watchlist_id"},
        )
        for item in items
    ]

    db_items = watchlist_item_crud.create_many(
        session=session,
        watchlist_id=watchlist_id,
        items=normalized_items,
    )

    session.commit()
    for db_item in db_items:
        session.refresh(db_item)

    return [
        WatchlistItemBase.model_validate(db_item, from_attributes=True)
        for db_item in db_items
    ]


def update_watchlist_item(
    session,
    *,
    item_id: int,
    user_profile_id: uuid.UUID,
    update_data: WatchlistItemUpdate,
):
    """
    Update a watchlist item.
    User must either own the watchlist or have edit access to it.
    """
    db_item = session.get(WatchlistItem, item_id)
    if not db_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Watchlist item not found.",
        )

    # Check if user can edit this watchlist
    can_edit = user_can_edit_watchlist(
        session=session,
        watchlist_id=db_item.watchlist_id,
        user_id=user_profile_id,
    )

    if not can_edit:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to edit this watchlist item.",
        )

    try:
        updated_item = watchlist_item_crud.update(
            session=session,
            id=item_id,
            obj_in=update_data,
        )

        if not updated_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Failed to update item.",
            )

        return updated_item

    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update watchlist item: {str(e)}",
        )


def delete_watchlist_item(
    session: Session,
    *,
    item_id: int,
    user_profile_id: uuid.UUID,
) -> WatchlistItem:
    """
    Deletes a watchlist item if the user has edit permission on its parent watchlist.
    """
    # 1. Fetch the item
    item = watchlist_item_crud.get(session, id=item_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Watchlist item not found.",
        )

    # 2. Check user edit access on the watchlist associated with the item
    has_access = user_can_edit_watchlist(
        session=session,
        watchlist_id=item.watchlist_id,
        user_id=user_profile_id,
    )
    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to delete this item.",
        )

    # 3. Delete the item
    deleted = watchlist_item_crud.remove(session, id=item_id)
    return deleted


def delete_watchlist(
    session: Session,
    *,
    watchlist_id: int,
    user_profile_id: uuid.UUID,
) -> Watchlist:
    """
    Deletes a watchlist if the user owns it.
    (Only owners can delete watchlists — not shared editors.)
    """
    # 1. Fetch the watchlist
    db_watchlist = watchlist_crud.get(session, id=watchlist_id)
    if not db_watchlist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Watchlist not found.",
        )

    # 2. Ensure user is the owner
    if str(db_watchlist.user_id) != str(user_profile_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the owner can delete this watchlist.",
        )

    deleted = watchlist_crud.remove(session, id=watchlist_id)
    return deleted


def share_watchlist_with_user(
    session: Session,
    *,
    watchlist_id: int,
    owner_profile_id: uuid.UUID,
    target_user_id: uuid.UUID,
    can_edit: bool = False,
):
    """
    Share a watchlist with another user.
    Only the owner can share a watchlist.
    """
    # 1. Validate the watchlist exists
    watchlist = watchlist_crud.get(session, id=watchlist_id)
    if not watchlist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Watchlist not found.",
        )

    # 2. Ensure the requesting user is the owner
    if str(watchlist.user_id) != str(owner_profile_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the owner can share this watchlist.",
        )

    # 3. Check if share already exists
    existing = watchlist_share_crud.get_share(
        session=session, watchlist_id=watchlist_id, user_id=target_user_id
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This user is already shared on this watchlist.",
        )

    # 4. Create new share record
    share_data = WatchlistShareCreate(
        watchlist_id=watchlist_id,
        user_id=target_user_id,
        can_edit=can_edit,
    )
    db_obj = watchlist_share_crud.create(
        session=session,
        obj_in=share_data,
    )

    return db_obj


def update_watchlist_share_permission(
    session,
    *,
    watchlist_id: int,
    owner_profile_id: uuid.UUID,
    target_user_id: uuid.UUID,
    can_edit: bool,
):
    """
    Update the 'can_edit' permission for a user on a shared watchlist.
    Only the owner of the watchlist can modify share permissions.
    """
    # 1. Validate watchlist
    watchlist = watchlist_crud.get(session, id=watchlist_id)
    if not watchlist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Watchlist not found.",
        )

    # 2. Ensure current user is owner
    if str(watchlist.user_id) != str(owner_profile_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the owner can update share permissions.",
        )

    # 3. Ensure share exists
    db_share = watchlist_share_crud.get_share(
        session=session, watchlist_id=watchlist_id, user_id=target_user_id
    )
    if not db_share:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User is not currently shared on this watchlist.",
        )

    # 4. Perform update
    updated_share = watchlist_share_crud.update(
        session=session,
        watchlist_id=watchlist_id,
        user_id=target_user_id,
        can_edit=can_edit,
    )

    return updated_share


def update_user_watchlist(
    session,
    *,
    watchlist_id: int,
    owner_profile_id: uuid.UUID,
    update_data: WatchlistUpdate,
):
    """
    Update a user's watchlist.
    Only the owner of the watchlist may perform updates.
    """
    # 1. Fetch existing watchlist
    watchlist = watchlist_crud.get(session, id=watchlist_id)
    if not watchlist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Watchlist not found.",
        )

    # 2. Verify ownership
    if str(watchlist.user_id) != str(owner_profile_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to update this watchlist.",
        )

    # 3. Apply updates via CRUD
    try:
        updated_watchlist = watchlist_crud.update(
            session=session,
            id=watchlist_id,
            obj_in=update_data,
        )

        if not updated_watchlist:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Failed to update — watchlist not found.",
            )

        return updated_watchlist

    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update watchlist: {str(e)}",
        )


def check_watchlist_bookmarked(
    session, *, watchlist_id: int, user_profile_id: uuid.UUID
) -> bool:
    """
    Check if the given watchlist is bookmarked by the user.
    """
    bookmark = session.exec(
        select(WatchlistBookmark).where(
            (WatchlistBookmark.watchlist_id == watchlist_id)
            & (WatchlistBookmark.user_id == user_profile_id)
        )
    ).first()
    if bookmark:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Watchlist is already bookmarked.",
        )


def check_watchlist_exists(
    session, *, watchlist_id: int, is_public: bool = True
) -> Watchlist:
    """
    Check if the given watchlist exists and is public.
    """
    watchlist = watchlist_crud.get(session, id=watchlist_id)
    if not watchlist or (is_public and watchlist.visibility != "public"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Watchlist not found or is not public.",
        )
    return watchlist


def bookmark_watchlist(session, *, watchlist_id: int, user_profile_id: uuid.UUID):
    """
    Bookmark a public watchlist.
    """
    try:
        # 1. Validate watchlist exists and is public
        watchlist = check_watchlist_exists(
            session=session,
            watchlist_id=watchlist_id,
            is_public=True,
        )

        # 2. Check if already bookmarked
        check_watchlist_bookmarked(
            session=session,
            watchlist_id=watchlist.id,
            user_profile_id=user_profile_id,
        )

        # 3. Create bookmark
        obj_in = WatchlistBookmarkBase(
            watchlist_id=watchlist.id,
            user_id=user_profile_id,
        )
        bookmark = watchlist_bookmark_crud.create(
            session=session,
            obj_in=obj_in,
        )
        return bookmark
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to bookmark watchlist: {str(e)}",
        )


def unbookmark_watchlist(session, *, watchlist_id: int, user_profile_id: uuid.UUID):
    """
    Remove a watchlist bookmark.
    """
    try:
        # 1. Validate watchlist exists and is public
        watchlist = check_watchlist_exists(
            session=session,
            watchlist_id=watchlist_id,
            is_public=True,
        )

        # 2. Get watchlist bookmark
        bookmark = watchlist_bookmark_crud.get_watchlist_bookmark(
            session=session,
            watchlist_id=watchlist.id,
            user_id=user_profile_id,
        )
        if not bookmark:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Watchlist Bookmark not found.",
            )

        # 3. Remove bookmark
        watchlist_bookmark_crud.remove(
            session=session,
            id=bookmark.id,
        )
        return {"message": "Bookmark removed successfully."}
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove bookmark: {str(e)}",
        )


def get_user_bookmarked_watchlists(
    session, *, user_profile_id: uuid.UUID, limit: int = 10, offset: int = 0
):
    """
    Return watchlists bookmarked by the user (with pagination).
    """
    bookmarks = watchlist_bookmark_crud.list_user_bookmarks(
        session=session,
        user_id=user_profile_id,
        limit=limit,
        offset=offset,
    )

    if not bookmarks:
        return []

    watchlist_ids = [b.watchlist_id for b in bookmarks]

    stmt = select(Watchlist).where(Watchlist.id.in_(watchlist_ids))
    return list(session.exec(stmt).all())


def fork_watchlist(
    session: Session,
    *,
    watchlist_id: int,
    user_profile_id: uuid.UUID,
) -> WatchlistForkOut:
    """
    Fork a public watchlist:
      1. Validate existence & visibility
      2. Prevent forking your own list
      3. Clone the watchlist (CRUD layer)
      4. Duplicate its items
      5. Increment fork_count on the original
    """
    # 1. Get the source watchlist
    source = watchlist_crud.get(session, id=watchlist_id)
    if not source:
        raise HTTPException(status_code=404, detail="Original watchlist not found.")

    # 2. Prevent self-fork
    if str(source.user_id) == str(user_profile_id):
        raise HTTPException(
            status_code=400, detail="You cannot fork your own watchlist."
        )

    # 2b. Ensure source is public
    if source.visibility != WatchlistVisibility.PUBLIC.value:
        raise HTTPException(
            status_code=403, detail="Only public watchlists can be forked."
        )

    # 3. Create forked watchlist (DB insert)
    forked = watchlist_crud.fork(
        session=session,
        source_watchlist=source,
        new_owner_id=user_profile_id,
    )

    # 4. Copy items from original to fork
    items_map = load_items_for_watchlists(session, [source.id])
    original_items = items_map.get(source.id, [])

    forked_items = []
    if original_items:
        forked_items = add_many_items_to_watchlist(
            session=session,
            watchlist_id=forked.id,
            items=original_items,
        )

    # 5. Increment fork count on source
    source.fork_count = (source.fork_count or 0) + 1
    session.add(source)
    session.commit()
    session.refresh(forked)

    return WatchlistForkOut(
        message="Watchlist forked successfully.",
        forked_watchlist=forked,
        forked_items=forked_items,
    )


def fork_watchlist_custom(
    session: Session,
    *,
    watchlist_id: int,
    user_profile_id: uuid.UUID,
    custom_data: Optional[WatchlistUpdate] = None,
):
    """
    Fork (clone) a public watchlist, optionally overriding name/description/visibility.

    If no custom_data is provided, the fork uses the source watchlist’s existing fields.
    """
    # 1. Get the source watchlist
    source = watchlist_crud.get(session, id=watchlist_id)
    if not source:
        raise HTTPException(status_code=404, detail="Watchlist not found.")

    # 2. Prevent self-fork
    if str(source.user_id) == str(user_profile_id):
        raise HTTPException(
            status_code=400, detail="You cannot fork your own watchlist."
        )

    # 2b. Ensure source is public
    if source.visibility != WatchlistVisibility.PUBLIC.value:
        raise HTTPException(
            status_code=403, detail="Only public watchlists can be forked."
        )

    # 3. Prepare base fork data & create forked watchlist
    if custom_data is None:
        forked = watchlist_crud.fork(
            session=session,
            source_watchlist=source,
            new_owner_id=user_profile_id,
        )
    else:
        fork_data = WatchlistCreate(
            name=custom_data.name or f"{source.name} (forked)",
            description=custom_data.description or source.description,
            visibility=custom_data.visibility or WatchlistVisibility.PRIVATE.value,
            is_default=False,
            forked_from_id=source.id,
            forked_at=datetime.now(timezone.utc),
            original_author_id=(source.original_author_id or source.user_id),
        )

        forked = watchlist_crud.create(
            session, owner_id=user_profile_id, obj_in=fork_data
        )

    # 4. Copy items from original to fork
    items_map = load_items_for_watchlists(session, [source.id])
    original_items = items_map.get(source.id, [])

    forked_items = []
    if original_items:
        forked_items = add_many_items_to_watchlist(
            session=session,
            watchlist_id=forked.id,
            items=original_items,
        )

    # 5. Increment fork count on the source
    source.fork_count = (source.fork_count or 0) + 1
    session.add(source)
    session.commit()
    session.refresh(forked)

    return {
        "message": "Watchlist forked successfully.",
        "forked_watchlist": forked,
        "forked_items": forked_items,
    }


def pull_forked_watchlist(
    session: Session,
    *,
    watchlist_id: int,
    user_profile_id: uuid.UUID,
) -> dict:
    """
    Pull the latest changes from the original (source) watchlist into this fork.

    Returns summary info.
    """
    # 1. Fetch the fork
    forked = watchlist_crud.get(session, id=watchlist_id)
    if not forked:
        raise HTTPException(status_code=404, detail="Watchlist not found.")

    # 2. Verify ownership
    if forked.user_id != user_profile_id:
        raise HTTPException(status_code=403, detail="You can only pull your own forks.")

    # 3. Check lineage
    if not forked.forked_from_id:
        raise HTTPException(
            status_code=400,
            detail="This watchlist was not forked from another watchlist.",
        )

    # 4. Get the source
    source = watchlist_crud.get(session, id=forked.forked_from_id)
    if not source:
        raise HTTPException(
            status_code=404, detail="Original watchlist no longer exists."
        )
    if source.visibility != WatchlistVisibility.PUBLIC.value:
        raise HTTPException(
            status_code=403, detail="The original watchlist is no longer public."
        )

    # 5. Perform sync - clear existing items & copy from source
    watchlist_crud.remove_all_items_in_watchlist(
        session=session,
        watchlist_id=forked.id,
    )

    source_items_map = load_items_for_watchlists(session, [source.id])
    source_items = source_items_map.get(source.id, [])
    added_items = []
    if source_items:
        added_items = add_many_items_to_watchlist(
            session=session,
            watchlist_id=forked.id,
            items=source_items,
        )

    return {
        "message": "Watchlist successfully synced with the original.",
        "forked_watchlist": added_items,
        "source_id": source.id,
        "source_name": source.name,
    }


def list_forks_for_watchlist(
    session: Session,
    *,
    watchlist_id: int,
    limit: int = 50,
    offset: int = 0,
):
    forks = watchlist_crud.list_forks_of_watchlist(
        session=session,
        watchlist_id=watchlist_id,
        limit=limit,
        offset=offset,
    )

    return [WatchlistOut.model_validate(f, from_attributes=True) for f in forks]


def list_trending_watchlists(session: Session, *, limit: int = 10):
    trending = watchlist_crud.list_trending(session=session, limit=limit)
    return [WatchlistOut.model_validate(w, from_attributes=True) for w in trending]


def get_watchlist_lineage(session: Session, *, watchlist_id: int) -> list[WatchlistOut]:
    """
    Recursively traverse the lineage chain for a given watchlist,
    from the current one up to the original ancestor.
    """
    lineage = []
    current = watchlist_crud.get(session, id=watchlist_id)

    while current:
        lineage.append(current)
        if not current.forked_from_id:
            break
        current = watchlist_crud.get(session, id=current.forked_from_id)

    lineage.reverse()  # show from oldest → newest
    return [WatchlistOut.model_validate(w, from_attributes=True) for w in lineage]


def validate_watchlist_allocation(
    watchlist_data: WatchlistCreate,
    items: List[WatchlistItemCreateWithoutId] | None,
) -> None:
    """
    Enforces allocation_type consistency between watchlist and items.
    Raises ValueError on invalid combinations.
    """
    if not items:
        return  # no items, nothing to validate

    allocation_type = watchlist_data.allocation_type

    if allocation_type == StockAllocationType.PERCENTAGE:
        sum = 0
        for item in items:
            if item.quantity is None or not (0 < item.allocation <= 100):
                raise ValueError(f"Invalid allocation value for percentage-based watchlist: {item.allocation}. Must be > 0 and <= 100.")
            sum += item.allocation

        if sum > 100:
            raise ValueError(f"Total allocation percentage cannot exceed 100%. Current sum: {sum}%.")
        
        return
        
    elif allocation_type == StockAllocationType.UNIT:
        for item in items:
            if item.quantity is None or item.quantity <= 0:
                raise ValueError(f"Invalid quantity for unit-based watchlist: {item.quantity}. Must be a positive integer.")

        return

    elif allocation_type is None:
        raise ValueError(f"Invalid allocation_type on watchlist: {allocation_type}. Must be 'percentage' or 'unit'.")

    else:
        raise ValueError(f"Unknown allocation_type: {allocation_type}")
