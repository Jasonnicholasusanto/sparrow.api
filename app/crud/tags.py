from __future__ import annotations
from typing import List

from sqlmodel import Session, select
from sqlalchemy import func, case
from app.crud.base import CRUDBase
from app.models.tags import Tags
from app.models.watchlist import Watchlist
from app.models.watchlist_tags import WatchlistTags
from app.schemas.tags import TagCreate, TagUpdate
from app.schemas.watchlist import WatchlistVisibility


class CRUDTags(CRUDBase[Tags, TagCreate, TagUpdate]):
    def get_by_name(self, session: Session, *, name: str) -> Tags | None:
        stmt = select(Tags).where(Tags.name.ilike(name.strip()))
        return session.exec(stmt).first()

    def get_by_slug(self, session: Session, *, slug: str) -> Tags | None:
        stmt = select(Tags).where(Tags.slug == slug.strip().lower())
        return session.exec(stmt).first()
    
    def search_with_public_counts(
        self,
        session: Session,
        *,
        query: str,
        limit: int = 8,
    ) -> list[tuple[Tags, int]]:
        q = query.strip()
        if not q:
            return []

        stmt = (
            select(
                Tags,
                func.count(func.distinct(Watchlist.id)).label("public_watchlist_count"),
            )
            .select_from(Tags)
            .outerjoin(WatchlistTags, WatchlistTags.tag_id == Tags.id)
            .outerjoin(
                Watchlist,
                (Watchlist.id == WatchlistTags.watchlist_id)
                & (Watchlist.visibility == WatchlistVisibility.PUBLIC.value),
            )
            .where(
                (Tags.name.ilike(f"%{q}%")) | (Tags.slug.ilike(f"%{q}%"))
            )
            .group_by(Tags.id)
            .order_by(
                case((Tags.name.ilike(f"{q}%"), 0), else_=1),
                Tags.is_system.desc(),
                func.count(func.distinct(Watchlist.id)).desc(),
                Tags.name.asc(),
            )
            .limit(limit)
        )

        return list(session.exec(stmt).all())

    def list_by_names(self, session: Session, *, names: List[str]) -> list[Tags]:
        normalized = [n.strip() for n in names if n and n.strip()]
        if not normalized:
            return []

        stmt = select(Tags).where(Tags.name.in_(normalized))
        return list(session.exec(stmt).all())

    def create(self, session: Session, *, obj_in: TagCreate) -> Tags:
        db_obj = self.model(**obj_in.model_dump())
        session.add(db_obj)
        session.commit()
        session.refresh(db_obj)

tags = CRUDTags(Tags)