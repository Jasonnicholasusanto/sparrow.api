from sqlmodel import Session, delete, select

from app.models.watchlist_audit_events import WatchlistAuditEvent



def create_watchlist_audit_event(
    session: Session,
    *,
    watchlist_id: int | None,
    user_profile_id,
    action: str,
    item_id: int | None = None,
    before_data: dict | None = None,
    after_data: dict | None = None,
    metadata: dict | None = None,
):
    event = WatchlistAuditEvent(
        watchlist_id=watchlist_id,
        user_profile_id=user_profile_id,
        action=action,
        item_id=item_id,
        before_data=before_data,
        after_data=after_data,
        metadata=metadata,
    )

    session.add(event)
    session.commit()
    session.refresh(event)

    return event


def list_watchlist_audit_events(
    session: Session,
    *,
    watchlist_id: int,
    limit: int = 50,
    offset: int = 0,
):
    stmt = (
        select(WatchlistAuditEvent)
        .where(WatchlistAuditEvent.watchlist_id == watchlist_id)
        .order_by(WatchlistAuditEvent.created_at.desc())
        .limit(limit)
        .offset(offset)
    )

    return list(session.scalars(stmt).all())


def list_watchlist_audit_events_for_user(
    session: Session,
    *,
    user_profile_id,
    limit: int = 50,
    offset: int = 0,
):
    stmt = (
        select(WatchlistAuditEvent)
        .where(WatchlistAuditEvent.user_profile_id == user_profile_id)
        .order_by(WatchlistAuditEvent.created_at.desc())
        .limit(limit)
        .offset(offset)
    )

    return list(session.exec(stmt).all())


def delete_all_watchlist_history_for_user(
    session: Session,
    *,
    user_profile_id,
) -> int:
    stmt = delete(WatchlistAuditEvent).where(
        WatchlistAuditEvent.user_profile_id == user_profile_id
    )

    result = session.exec(stmt)
    session.commit()

    return result.rowcount or 0


def delete_all_watchlist_history_for_watchlist(
    session: Session,
    *,
    watchlist_id: int,
    user_profile_id,
) -> int:
    stmt = delete(WatchlistAuditEvent).where(
        WatchlistAuditEvent.watchlist_id == watchlist_id,
        WatchlistAuditEvent.user_profile_id == user_profile_id,
    )

    result = session.exec(stmt)
    session.commit()

    return result.rowcount or 0