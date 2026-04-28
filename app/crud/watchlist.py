# app/crud/watchlist.py
from __future__ import annotations

from datetime import datetime, timezone
import uuid
from typing import List, Optional

from sqlalchemy import func, update as sa_update
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, delete, desc, select

from app.crud.base import CRUDBase
from app.models.user_profile import UserProfile
from app.models.vote import Vote
from app.models.watchlist import Watchlist
from app.models.watchlist_item import WatchlistItem
from app.schemas.watchlist import WatchlistCreate, WatchlistUpdate, WatchlistVisibility


class CRUDWatchlist(CRUDBase[Watchlist, WatchlistCreate, WatchlistUpdate]):
    # ----- GETs -----
    def get_by_id(self, session: Session, *, id: int) -> Watchlist | None:
        return session.get(Watchlist, id)

    def get_public_by_user_and_name(
        self, session: Session, *, user_id: uuid.UUID, name: str
    ) -> Watchlist | None:
        """Fetch a user's watchlist by name (case-insensitive; trims input)."""
        stmt = (
            select(Watchlist)
            .where(
                Watchlist.user_id == user_id,
                func.lower(Watchlist.name) == func.lower(func.trim(name)),
                Watchlist.visibility == WatchlistVisibility.PUBLIC.value,
            )
            .limit(1)
        )
        return session.exec(stmt).first()

    def get_public_by_username_and_name(
        self,
        session: Session,
        *,
        username: str,
        name: str,
    ) -> Watchlist | None:
        """
        Fetch a watchlist by owner's username and the list name (both case-insensitive).

        Args:
            username: Owner's username (case-insensitive).
            name:     Watchlist name (case-insensitive).
            public_only: If True, only return if the watchlist is PUBLIC,
                         unless current_user_id matches the owner.
            current_user_id: The caller's user id (to allow owner's private lists when public_only=True).

        Returns:
            Watchlist | None
        """
        stmt = (
            select(Watchlist)
            .join(UserProfile, UserProfile.id == Watchlist.user_id)
            .where(
                func.lower(UserProfile.username) == func.lower(func.trim(username)),
                func.lower(Watchlist.name) == func.lower(func.trim(name)),
                Watchlist.visibility == WatchlistVisibility.PUBLIC.value,
            )
            .limit(1)
        )

        return session.exec(stmt).first()

    def get_default_for_user(
        self, session: Session, *, user_id: uuid.UUID
    ) -> Watchlist | None:
        stmt = (
            select(Watchlist)
            .where(Watchlist.user_id == user_id, Watchlist.is_default.is_(True))
            .limit(1)
        )
        return session.exec(stmt).first()
    
    # ---- LISTs -----
    def list_public_by_name(
        self, session: Session, *, name: str, limit: int = 20, offset: int = 0
    ) -> List[Watchlist]:
        """Case-insensitive partial match on name, public only."""
        n = name.strip()
        stmt = (
            select(Watchlist)
            .where(
                Watchlist.visibility == WatchlistVisibility.PUBLIC.value,
                Watchlist.name.ilike(f"%{n}%"),
            )
            .order_by(Watchlist.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(session.exec(stmt).all())

    def list_by_user(
        self,
        session: Session,
        *,
        user_id: uuid.UUID,
        q: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Watchlist]:
        """
        List watchlists owned by user.
        Optional 'q' filters by name ILIKE '%q%'.
        """
        stmt = select(Watchlist).where(Watchlist.user_id == user_id)
        if q:
            stmt = stmt.where(Watchlist.name.ilike(f"%{q.strip()}%"))
        stmt = (
            stmt.order_by(
                Watchlist.is_default.desc(),  # show default first
                Watchlist.created_at.asc(),
            )
            .limit(limit)
            .offset(offset)
        )
        return list(session.exec(stmt).all())

    def list_forks_of_watchlist(
        self, session: Session, *, watchlist_id: int, limit: int = 50, offset: int = 0
    ) -> list[Watchlist]:
        """
        Return all watchlists that were forked from the given watchlist.
        """
        stmt = (
            select(Watchlist)
            .where(Watchlist.forked_from_id == watchlist_id)
            .order_by(Watchlist.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(session.exec(stmt).all())

    def list_trending(self, session: Session, *, limit: int = 10) -> list[Watchlist]:
        """
        Return top watchlists sorted by combined fork_count and vote totals.

        The formula used balances:
        1. Popularity (log scaling) — big lists don’t dominate forever
        2. Freshness (time decay) — recent lists trend faster
        3. Engagement type (weights) — deep vs. shallow engagement


        """
        now = datetime.now(timezone.utc)

        # EXTRACT epoch returns in seconds; convert to days by dividing by 86400
        age_days = func.extract("epoch", func.age(now, Watchlist.updated_at)) / 86400.0
        total_votes = func.coalesce(func.sum(Vote.vote), 0)
        fork_count = func.coalesce(Watchlist.fork_count, 0)

        score = (
            func.log(1 + (3 * fork_count + total_votes)) / func.log(10)
        ) / func.pow(1 + age_days, 0.5)

        stmt = (
            select(Watchlist)
            .outerjoin(Vote, Vote.watchlist_id == Watchlist.id)
            .where(Watchlist.visibility == WatchlistVisibility.PUBLIC.value)
            .group_by(Watchlist.id)
            .order_by(desc(score))
            .limit(limit)
        )

        return list(session.exec(stmt).all())

    # ----- CREATE / FORK / UPDATE / REMOVE / PULL -----
    def create(
        self,
        session: Session,
        *,
        owner_id: uuid.UUID,
        obj_in: WatchlistCreate,
    ) -> Watchlist:
        """
        Create a watchlist for the owner.
        If obj_in.is_default=True, unset other defaults for this user first.
        Then call the base create() for actual insertion.
        """
        try:
            # 1. Unset other defaults (within same transaction)
            if obj_in.is_default:
                session.exec(
                    sa_update(Watchlist)
                    .where(Watchlist.user_id == owner_id)
                    .values(is_default=False)
                )

            if not obj_in.original_author_id:
                obj_in.original_author_id = owner_id

            # 2. Create the new watchlist
            db_obj = super().create(session, obj_in=obj_in, user_id=owner_id)

            return db_obj

        except IntegrityError as e:
            session.rollback()
            # Handle unique constraint violations (e.g., duplicate name per user)
            if "ux_watchlist_user_name" in str(e.orig):
                raise ValueError("You already have a watchlist with this name.")
            raise ValueError(f"Failed to create watchlist: {str(e)}")

    def fork(
        self,
        session: Session,
        *,
        source_watchlist: Watchlist,
        new_owner_id: uuid.UUID,
    ) -> Watchlist:
        """
        Clone an existing (public) watchlist to a new owner.

        The forked watchlist will:
          - Copy name/description/visibility (set to private)
          - Record fork lineage fields
        """
        fork_data = WatchlistCreate(
            name=f"{source_watchlist.name} (forked)",
            description=source_watchlist.description,
            visibility=WatchlistVisibility.PRIVATE.value,
            is_default=False,
            forked_from_id=source_watchlist.id,
            forked_at=datetime.now(timezone.utc),
        )

        # Prefer the original_author_id chain if set
        if source_watchlist.original_author_id:
            fork_data.original_author_id = source_watchlist.original_author_id
        else:
            fork_data.original_author_id = source_watchlist.user_id

        forked = self.create(session, owner_id=new_owner_id, obj_in=fork_data)
        return forked

    def update(
        self, session: Session, *, id: int, obj_in: WatchlistUpdate
    ) -> Optional[Watchlist]:
        """
        Update fields by id.
        If setting is_default=True, unset other defaults for the same user first.
        """
        db_obj = session.get(Watchlist, id)
        if not db_obj:
            return None

        # If user sets is_default=True, make sure to unset others
        if obj_in.is_default is True:
            session.exec(
                sa_update(Watchlist)
                .where(
                    Watchlist.user_id == db_obj.user_id,
                    Watchlist.id != id,
                )
                .values(is_default=False)
            )

        update_data = obj_in.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(db_obj, field, value)

        db_obj.updated_at = datetime.now(timezone.utc)

        session.add(db_obj)
        session.commit()
        session.refresh(db_obj)
        return db_obj

        # Delegate to CRUDBase for patch semantics and commit
        # return super().update(session, id=id, obj_in=obj_in)

    def remove(
        self,
        session: Session,
        *,
        id: int,
    ) -> Optional[Watchlist]:
        """
        Delete a watchlist by ID.
        Returns the deleted watchlist or None if not found.
        """
        db_obj = self.get(session, id=id)
        if not db_obj:
            return None

        return super().remove(session, id=id)

    def remove_all_items_in_watchlist(
        self,
        session: Session,
        *,
        watchlist_id: int,
    ) -> int:
        """
        Delete all items associated with a watchlist.
        Returns the number of items deleted.
        """
        stmt = select(Watchlist).where(Watchlist.id == watchlist_id)
        watchlist = session.exec(stmt).first()
        if not watchlist:
            return 0

        result = session.exec(
            delete(WatchlistItem).where(WatchlistItem.watchlist_id == watchlist_id)
        )

        session.commit()
        return result.rowcount or 0


watchlist = CRUDWatchlist(Watchlist)
