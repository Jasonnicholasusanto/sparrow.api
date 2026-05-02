from __future__ import annotations
from typing import List

from sqlmodel import Session, select

from app.crud.base import CRUDBase
from app.models.tags import Tags
from app.schemas.tags import TagCreate, TagUpdate


class CRUDTags(CRUDBase[Tags, TagCreate, TagUpdate]):
    def get_by_name(self, session: Session, *, name: str) -> Tags | None:
        stmt = select(Tags).where(Tags.name.ilike(name.strip()))
        return session.exec(stmt).first()

    def get_by_slug(self, session: Session, *, slug: str) -> Tags | None:
        stmt = select(Tags).where(Tags.slug == slug.strip().lower())
        return session.exec(stmt).first()

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