# app/models/point_rule.py
from __future__ import annotations

from datetime import datetime
from sqlmodel import SQLModel, Field

# Reuse the enum you defined in app/schemas/point_rule.py
from app.schemas.point_rule import PointRuleSource


class PointRule(SQLModel, table=True):
    """
    ORM mapping for public.point_rule (id BIGSERIAL PK).
    Managed by DB; this model is read/write but does not create the table.
    """

    __tablename__ = "point_rule"
    __table_args__ = {"schema": "public"}

    id: int = Field(primary_key=True)
    source: PointRuleSource = Field(index=True)
    points: int = Field()
    created_at: datetime
    updated_at: datetime
