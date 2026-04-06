from typing import List
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.dependencies.profile import get_current_profile
from app.api.deps import SessionDep
from app.schemas.watchlist import (
    StockAllocationType,
    UserWatchlistsGroupedResultsOut,
    UserWatchlistsResponseOut,
    WatchlistCountsOut,
    WatchlistForkOut,
    WatchlistOut,
    WatchlistPublicOut,
    WatchlistUpdate,
    WatchlistVisibility,
)
from app.schemas.watchlist_detail import (
    WatchlistDetailCreateRequest,
    WatchlistsDetail,
)
from app.schemas.watchlist_item import (
    WatchlistItemBase,
    WatchlistItemCreate,
    WatchlistItemCreateWithoutId,
    WatchlistItemOut,
    WatchlistItemUpdate,
)
from app.schemas.watchlist_share import (
    WatchlistShareCreate,
    WatchlistShareOut,
    WatchlistShareUpdate,
)
from app.services.user_profile_service import get_user_profile_by_username
from app.services.watchlist_service import (
    add_item_to_watchlist,
    add_many_items_to_watchlist,
    bookmark_watchlist,
    create_watchlist_for_user,
    delete_watchlist,
    delete_watchlist_item,
    enrich_user_watchlists_with_market_snapshots,
    fork_watchlist,
    fork_watchlist_custom,
    get_all_user_related_watchlists,
    get_user_bookmarked_watchlists,
    get_watchlist_items_securely,
    get_watchlist_lineage,
    get_watchlists_shared_with_user,
    list_forks_for_watchlist,
    list_trending_watchlists,
    load_items_for_watchlists,
    pull_forked_watchlist,
    search_public_watchlists_by_name,
    share_watchlist_with_user,
    unbookmark_watchlist,
    update_user_watchlist,
    update_watchlist_item,
    update_watchlist_share_permission,
    user_can_edit_watchlist,
    validate_watchlist_allocation,
    watchlist_item_exists,
)
from app.services.yfinance_service import fetch_ticker_market_snapshots


router = APIRouter(prefix="/watchlists", tags=["Watchlists"])


@router.get("/types", response_model=list[str])
def get_watchlist_visibility_types():
    """
    Get all possible watchlist visibility types.
    """
    return [vt.value for vt in WatchlistVisibility]


@router.get("/allocation-types", response_model=list[str])
def get_watchlist_allocation_types():
    """
    Get all possible watchlist stock allocation types.
    """

    return [at.value for at in StockAllocationType]


@router.get("/me")
def get_my_watchlists(
    db: SessionDep,
    limit: int = Query(10, ge=1, le=20),
    offset: int = Query(0, ge=0),
    user=Depends(get_current_profile),
):
    """
    Get the current user's watchlists (paginated).
    Optional lazy loading with `limit` and `offset`.
    """

    # 1. Fetch user's watchlists (paginated)
    user_watchlists = get_all_user_related_watchlists(
        session=db,
        user_profile_id=user.id,
        limit=limit,
        offset=offset,
    )

    if not user_watchlists:
        return UserWatchlistsResponseOut(
            limit=limit, 
            offset=offset, 
            results=UserWatchlistsGroupedResultsOut(
                created=[],
                forked=[],
                shared=[],
                bookmarked=[],
                total_count=0,
                counts=WatchlistCountsOut(owned=0, forked=0, shared=0, bookmarked=0)
            )
        )

    # 2. Retrieve ticker information for all items in these watchlists
    enriched_watchlists = enrich_user_watchlists_with_market_snapshots(user_watchlists)

    # 3. Return enriched watchlists with pagination metadata
    return UserWatchlistsResponseOut(
        limit=limit,
        offset=offset,
        results=UserWatchlistsGroupedResultsOut.model_validate(enriched_watchlists, from_attributes=True),
    )


@router.get("/user/@{username}", response_model=UserWatchlistsResponseOut)
def get_public_watchlists_by_username(
    username: str,
    db: SessionDep,
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
    user=Depends(get_current_profile),
):
    """
    Get PUBLIC watchlists for a given username (case-insensitive).
    Returns multiple results.
    """
    if not username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Username is required."
        )

    profile = get_user_profile_by_username(db, username=username)

    # 1. Search for public watchlists by username
    watchlists = get_all_user_related_watchlists(
        db, user_profile_id=profile.id, limit=limit, offset=offset, is_public_only=True
    )

    if not watchlists:
        return UserWatchlistsResponseOut(
            limit=limit, 
            offset=offset, 
            results=UserWatchlistsGroupedResultsOut(
                created=[],
                forked=[],
                shared=[],
                bookmarked=[],
                total_count=0,
                counts=WatchlistCountsOut(owned=0, forked=0, shared=0, bookmarked=0)
            )
        )
    
    # 2. Retrieve ticker information for all items in these watchlists
    enriched_watchlists = enrich_user_watchlists_with_market_snapshots(watchlists)
    
    return UserWatchlistsResponseOut(
        limit=limit,
        offset=offset,
        results=UserWatchlistsGroupedResultsOut.model_validate(enriched_watchlists, from_attributes=True)
    )


@router.get("/{watchlist_id}/items", response_model=list[WatchlistItemOut])
def get_watchlist_items_route(
    watchlist_id: int,
    db: SessionDep,
    user=Depends(get_current_profile),
):
    """
    Retrieve items in a watchlist.

    Access allowed if:
      - The user owns the watchlist, OR
      - The watchlist is shared with them, OR
      - The watchlist is public
    """

    try:
        items = get_watchlist_items_securely(
            session=db,
            watchlist_id=watchlist_id,
            user_profile_id=user.id,
        )
        symbols = [item.symbol for item in items if item.symbol and item.exchange]
        snapshot_map = fetch_ticker_market_snapshots(symbols)
        
        enriched_items = [
            WatchlistItemOut(
                **item.model_dump(exclude={"ticker_details"}),
                ticker_details=snapshot_map.get((item.symbol or "").upper()),
            )
            for item in items
        ]

        return enriched_items
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve items: {str(e)}"
        )


@router.get("/@{name}", response_model=WatchlistsDetail)
def get_public_watchlists_by_name(
    name: str,
    db: SessionDep,
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
    user=Depends(get_current_profile),
):
    """
    Search PUBLIC watchlists by name (case-insensitive, partial match).
    Returns multiple results.
    """
    if not name.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Name is required."
        )

    watchlists = search_public_watchlists_by_name(
        db, name=name, limit=limit, offset=offset
    )

    if not watchlists:
        return WatchlistsDetail(total=0, watchlists=[])

    # Batch-load items to avoid N+1
    id_list = [w.id for w in watchlists if w.id is not None]
    items_by_watchlist_id = load_items_for_watchlists(db, id_list)

    results = [
        WatchlistOut.model_validate(
            watchlist, from_attributes=True
        ).model_copy(
            update={"items": [WatchlistItemBase.model_validate(item, from_attributes=True) for item in items_by_watchlist_id.get(watchlist.id, [])]}
        )
        for watchlist in watchlists
    ]

    return WatchlistsDetail(total=len(results), watchlists=results)


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_watchlist(
    db: SessionDep,
    payload: WatchlistDetailCreateRequest,
    user=Depends(get_current_profile),
):
    """
    Create a new watchlist for the authenticated user.
    Optionally accepts a list of initial watchlist items.
    """
    try:
        watchlist_data = payload.watchlist_data
        items = payload.items

        # 1. Validate allocation type consistency
        validate_watchlist_allocation(watchlist_data, items)

        # 2. Create the new watchlist
        new_watchlist = create_watchlist_for_user(
            db,
            user_id=user.id,
            watchlist_data=watchlist_data,
        )

        # 3. Add items if provided
        new_items = []
        if items:
            new_items = add_many_items_to_watchlist(
                session=db,
                watchlist_id=new_watchlist.id,
                items=items,
            )

        # 4. Return combined response
        return {
            "message": "Watchlist created successfully.",
            "watchlist": new_watchlist,
            "watchlist_items": new_items,
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create watchlist: {str(e)}",
        )


@router.post("/add-item")
def add_watchlist_item_to_watchlist(
    item: WatchlistItemCreate,
    db: SessionDep,
    user=Depends(get_current_profile),
):
    # Add the item
    new_item = add_item_to_watchlist(
        session=db,
        item=item,
        user_profile_id=user.id,
    )
    return {"message": "Item added successfully", "item": new_item}


@router.post("/add-items/{watchlist_id}")
def add_bulk_watchlist_items_to_watchlist(
    watchlist_id: int,
    items: List[WatchlistItemCreateWithoutId],
    db: SessionDep,
    user=Depends(get_current_profile),
):
    # Validate edit permissions
    user_access = user_can_edit_watchlist(
        session=db,
        watchlist_id=watchlist_id,
        user_id=user.id,
    )
    if not user_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to edit this watchlist.",
        )

    # 3. Check for duplicates within the provided items
    watchlist_items_existing_symbols = set()
    for item in items:
        if watchlist_item_exists(
            session=db,
            watchlist_id=watchlist_id,
            symbol=item.symbol,
            exchange=item.exchange,
        ):
            watchlist_items_existing_symbols.add(item.symbol)
    if watchlist_items_existing_symbols:
        symbols_list = ", ".join(sorted(watchlist_items_existing_symbols))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Symbols [{symbols_list}] already exists in this watchlist.",
        )

    # 4. Add the items in bulk
    new_items = add_many_items_to_watchlist(
        session=db,
        watchlist_id=watchlist_id,
        items=items,
    )

    return {"count": len(new_items), "items": new_items}


@router.delete("/item/{item_id}", status_code=status.HTTP_200_OK)
def delete_watchlist_item_from_watchlist(
    item_id: int,
    db: SessionDep,
    user=Depends(get_current_profile),
):
    """
    Delete a specific watchlist item if the user has edit access.
    """
    # Perform deletion
    deleted_item = delete_watchlist_item(
        session=db,
        item_id=item_id,
        user_profile_id=user.id,
    )

    if not deleted_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found or already deleted.",
        )

    return {"message": "Item deleted successfully.", "deleted_item": deleted_item}


@router.delete("/{watchlist_id}", status_code=status.HTTP_200_OK)
def delete_watchlist_route(
    watchlist_id: int,
    db: SessionDep,
    user=Depends(get_current_profile),
):
    """
    Delete a watchlist owned by the authenticated user.
    All related items and shares will be deleted via ON DELETE CASCADE.
    """
    # Delete the watchlist (ownership check inside)
    deleted_watchlist = delete_watchlist(
        session=db,
        watchlist_id=watchlist_id,
        user_profile_id=user.id,
    )

    if not deleted_watchlist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Watchlist not found or already deleted.",
        )

    return {
        "message": "Watchlist deleted successfully.",
        "deleted_watchlist": deleted_watchlist,
    }


@router.get("/shared/me", response_model=dict)
def get_shared_watchlists_for_user(
    db: SessionDep,
    limit: int = Query(10, ge=1, le=20),
    offset: int = Query(0, ge=0),
    user=Depends(get_current_profile),
):
    """
    Get all watchlists that have been shared with the current user.
    Includes edit permissions for each shared watchlist.
    """
    # Get shared watchlists
    shared_watchlists = get_watchlists_shared_with_user(
        session=db,
        user_profile_id=user.id,
        limit=limit,
        offset=offset,
    )

    return {
        "message": "Fetched watchlists shared with user successfully.",
        "count": len(shared_watchlists),
        "watchlists": shared_watchlists,
    }


@router.post("/share", response_model=WatchlistShareOut)
def share_watchlist(
    share_data: WatchlistShareCreate,
    db: SessionDep,
    user=Depends(get_current_profile),
):
    """
    Share a watchlist with another user.
    Only the owner of the watchlist can perform this action.
    """
    # 2. Perform the share
    shared = share_watchlist_with_user(
        session=db,
        watchlist_id=share_data.watchlist_id,
        owner_profile_id=user.id,
        target_user_id=share_data.user_id,
        can_edit=share_data.can_edit,
    )

    return shared


@router.patch(
    "/{watchlist_id}/share/{target_user_id}", response_model=WatchlistShareOut
)
def update_watchlist_share(
    watchlist_id: int,
    target_user_id: uuid.UUID,
    update_data: WatchlistShareUpdate,
    db: SessionDep,
    user=Depends(get_current_profile),
):
    """
    Update sharing permissions (can_edit) for a user on a watchlist.
    Only the watchlist owner can perform this action.
    """
    # Perform update
    updated_share = update_watchlist_share_permission(
        session=db,
        watchlist_id=watchlist_id,
        owner_profile_id=user.id,
        target_user_id=target_user_id,
        can_edit=update_data.can_edit,
    )

    return updated_share


@router.patch("/{watchlist_id}", response_model=WatchlistOut)
def update_watchlist(
    watchlist_id: int,
    watchlist_data: WatchlistUpdate,
    db: SessionDep,
    user=Depends(get_current_profile),
):
    """
    Update an existing watchlist.
    Only the owner can perform this action.
    """
    # Perform update
    updated_watchlist = update_user_watchlist(
        session=db,
        watchlist_id=watchlist_id,
        owner_profile_id=user.id,
        update_data=watchlist_data,
    )

    return updated_watchlist


@router.patch("/items/{item_id}", response_model=WatchlistItemBase)
def update_watchlist_item_route(
    item_id: int,
    update_data: WatchlistItemUpdate,
    db: SessionDep,
    user=Depends(get_current_profile),
):
    """
    Update an existing item in a watchlist.
    User must own or have edit access to the watchlist.
    """
    # 2. Update item via service
    updated_item = update_watchlist_item(
        session=db,
        item_id=item_id,
        user_profile_id=user.id,
        update_data=update_data,
    )

    return updated_item


@router.post("/{watchlist_id}/bookmark", status_code=status.HTTP_201_CREATED)
def bookmark_watchlist_route(
    watchlist_id: int,
    db: SessionDep,
    user=Depends(get_current_profile),
):
    """
    Bookmark a public watchlist.
    """
    bookmark = bookmark_watchlist(
        session=db,
        watchlist_id=watchlist_id,
        user_profile_id=user.id,
    )
    return {"message": "Watchlist bookmarked successfully.", "bookmark": bookmark}


@router.delete("/{watchlist_id}/bookmark", status_code=status.HTTP_200_OK)
def unbookmark_watchlist_route(
    watchlist_id: int,
    db: SessionDep,
    user=Depends(get_current_profile),
):
    """
    Remove a bookmark for a public watchlist.
    """
    return unbookmark_watchlist(
        session=db,
        watchlist_id=watchlist_id,
        user_profile_id=user.id,
    )


@router.get("/bookmarks/me", status_code=status.HTTP_200_OK)
def list_user_bookmarks_route(
    db: SessionDep,
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user=Depends(get_current_profile),
):
    """
    List all watchlists bookmarked by the current user.
    """
    results = get_user_bookmarked_watchlists(
        session=db,
        user_profile_id=user.id,
        limit=limit,
        offset=offset,
    )
    return {"count": len(results), "results": results}


@router.post("/{watchlist_id}/fork", response_model=WatchlistForkOut)
def fork_watchlist_route(
    watchlist_id: int,
    db: SessionDep,
    user=Depends(get_current_profile),
):
    """
    Fork (clone) a public watchlist into the current user's account.
    """
    try:
        result = fork_watchlist(
            session=db, watchlist_id=watchlist_id, user_profile_id=user.id
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to fork watchlist: {str(e)}"
        )


@router.post("/{watchlist_id}/fork/custom", response_model=WatchlistForkOut)
def fork_watchlist_custom_route(
    watchlist_id: int,
    db: SessionDep,
    payload: WatchlistUpdate | None = None,
    user=Depends(get_current_profile),
):
    """
    Fork (clone) a public watchlist with optional custom details.

    Example body:
    {
        "name": "My personalized tech portfolio",
        "description": "Adapted from FinForum Top Tech Picks"
    }
    """
    # Execute fork
    try:
        result = fork_watchlist_custom(
            session=db,
            watchlist_id=watchlist_id,
            user_profile_id=user.id,
            custom_data=payload,
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to fork watchlist: {str(e)}"
        )


@router.post("/{watchlist_id}/pull", response_model=dict)
def pull_forked_watchlist_route(
    watchlist_id: int,
    db: SessionDep,
    user=Depends(get_current_profile),
):
    """
    Pull (sync) the latest changes from the original watchlist into this fork.

    Only works if:
      - The watchlist was forked from another
      - The original is still PUBLIC
    """
    try:
        result = pull_forked_watchlist(
            session=db,
            watchlist_id=watchlist_id,
            user_profile_id=user.id,
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to pull watchlist: {str(e)}"
        )


@router.get("/{watchlist_id}/forks", response_model=list[WatchlistOut])
def get_forked_watchlists(
    watchlist_id: int,
    db: SessionDep,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user=Depends(get_current_profile),
):
    """
    List all forks of a given watchlist.
    """
    try:
        return list_forks_for_watchlist(
            session=db, watchlist_id=watchlist_id, limit=limit, offset=offset
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list forks: {str(e)}")


@router.get("/{watchlist_id}/lineage", response_model=list[WatchlistOut])
def get_watchlist_lineage_route(
    watchlist_id: int,
    db: SessionDep,
    user=Depends(get_current_profile),
):
    """
    Return the full lineage of this watchlist (original → current).
    """
    return get_watchlist_lineage(session=db, watchlist_id=watchlist_id)


@router.get("/trending", response_model=list[WatchlistOut])
def get_trending_watchlists(
    db: SessionDep,
    limit: int = Query(10, ge=1, le=50),
    user=Depends(get_current_profile),
):
    """
    Return trending watchlists, ranked by fork count + votes.
    """
    return list_trending_watchlists(session=db, limit=limit)
