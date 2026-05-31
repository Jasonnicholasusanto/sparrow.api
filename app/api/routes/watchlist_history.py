from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies.profile import get_current_profile
from app.api.deps import SessionDep
from app.schemas.watchlist_history import WatchlistAuditEventOut
from app.services.watchlist_audit_service import (
    delete_all_watchlist_history_for_user,
    delete_all_watchlist_history_for_watchlist,
    list_watchlist_audit_events_for_user,
    list_watchlist_audit_events,
)

router = APIRouter(prefix="/watchlist-history", tags=["Watchlist History"])


@router.delete("/me", status_code=status.HTTP_200_OK)
def delete_my_watchlist_history(
    db: SessionDep,
    user=Depends(get_current_profile),
):
    deleted_count = delete_all_watchlist_history_for_user(
        session=db,
        user_profile_id=user.id,
    )

    return {
        "message": "Watchlist history deleted successfully.",
        "deleted_count": deleted_count,
    }


@router.delete("/watchlist/{watchlist_id}", status_code=status.HTTP_200_OK)
def delete_watchlist_history(
    watchlist_id: int,
    db: SessionDep,
    user=Depends(get_current_profile),
):
    deleted_count = delete_all_watchlist_history_for_watchlist(
        session=db,
        watchlist_id=watchlist_id,
        user_profile_id=user.id,
    )

    return {
        "message": "Watchlist history deleted successfully.",
        "deleted_count": deleted_count,
    }


@router.get("/me", response_model=list[WatchlistAuditEventOut])
def get_my_watchlist_history(
    db: SessionDep,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user=Depends(get_current_profile),
):
    return list_watchlist_audit_events_for_user(
        session=db,
        user_profile_id=user.id,
        limit=limit,
        offset=offset,
    )


@router.get("/watchlist/{watchlist_id}", response_model=list[WatchlistAuditEventOut])
def get_watchlist_history(
    watchlist_id: int,
    db: SessionDep,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user=Depends(get_current_profile),
):
    return list_watchlist_audit_events(
        session=db,
        watchlist_id=watchlist_id,
        limit=limit,
        offset=offset,
    )