from __future__ import annotations

import re
from typing import Iterable, List, Sequence

from sqlmodel import Session, select

from app.crud.tags import tags as tag_crud
from app.models.tags import Tags
from app.models.watchlist_tags import WatchlistTags
from app.schemas.tags import TagSearchOut


def slugify_tag(name: str) -> str:
    """
    Convert a tag name into a URL/db-friendly slug.

    Examples:
        "US Tech" -> "us-tech"
        " AI " -> "ai"
        "Dividend & Income" -> "dividend-income"
    """
    slug = name.strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug


def normalize_tag_names(tag_names: Sequence[str] | None) -> list[str]:
    """
    Normalize, trim, and deduplicate incoming tag names while preserving order.

    Empty/null values are ignored.
    Deduplication is done by slug equivalence, not exact raw string.
    """
    if not tag_names:
        return []

    normalized: list[str] = []
    seen_slugs: set[str] = set()

    for raw_name in tag_names:
        if raw_name is None:
            continue

        cleaned = raw_name.strip()
        if not cleaned:
            continue

        slug = slugify_tag(cleaned)
        if not slug or slug in seen_slugs:
            continue

        seen_slugs.add(slug)
        normalized.append(cleaned)

    return normalized


def add_tags_to_watchlist(
    session: Session,
    *,
    watchlist_id: int,
    tag_names: Sequence[str] | None,
) -> list[Tags]:
    """
    Resolve tag names into tags and attach them to the watchlist.

    Does not commit; caller controls transaction.
    Returns the list of resolved Tags.
    """
    resolved_tags = get_or_create_tags(
        session,
        tag_names=tag_names,
    )

    attach_tags_to_watchlist(
        session,
        watchlist_id=watchlist_id,
        tags=resolved_tags,
    )

    return resolved_tags


def get_or_create_tags(
    session: Session,
    *,
    tag_names: Sequence[str] | None,
    default_category: str = "custom",
    default_is_system: bool = False,
) -> list[Tags]:
    """
    Resolve a list of tag names into tag rows.

    Behavior:
    - reuses existing tags by slug
    - creates missing tags
    - returns unique tags in input order
    - does not commit; caller controls transaction
    """
    normalized_names = normalize_tag_names(tag_names)
    if not normalized_names:
        return []

    resolved_tags: list[Tags] = []

    for name in normalized_names:
        slug = slugify_tag(name)

        existing = tag_crud.get_by_slug(session, slug=slug)
        if existing:
            resolved_tags.append(existing)
            continue

        new_tag = Tags(
            name=name,
            slug=slug,
            category=default_category,
            is_system=default_is_system,
        )
        session.add(new_tag)
        session.flush() 
        resolved_tags.append(new_tag)

    return resolved_tags


def attach_tags_to_watchlist(
    session: Session,
    *,
    watchlist_id: int,
    tags: Sequence[Tags] | None,
) -> list[WatchlistTags]:
    """
    Attach tags to a watchlist, skipping any existing links.

    Does not commit.
    """
    if not tags:
        return []

    existing_links = session.exec(
        select(WatchlistTags).where(WatchlistTags.watchlist_id == watchlist_id)
    ).all()

    existing_tag_ids = {link.tag_id for link in existing_links}
    created_links: list[WatchlistTags] = []

    for tag in tags:
        if tag.id in existing_tag_ids:
            continue

        link = WatchlistTags(
            watchlist_id=watchlist_id,
            tag_id=tag.id,
        )
        session.add(link)
        created_links.append(link)
    
    session.commit()

    return created_links


def sync_watchlist_tags(
    session: Session,
    *,
    watchlist_id: int,
    tag_names: Sequence[str] | None,
    default_category: str = "custom",
    default_is_system: bool = False,
) -> list[Tags]:
    """
    Make the watchlist's tags exactly match the provided tag names.

    Rules:
    - if tag_names is None: caller should usually interpret that as "do not change tags"
      and should not call this function
    - if tag_names is []: remove all existing tags
    - missing existing links are deleted
    - missing tags are created
    - new links are inserted
    - does not commit
    """
    resolved_tags = get_or_create_tags(
        session,
        tag_names=tag_names,
        default_category=default_category,
        default_is_system=default_is_system,
    )

    target_tag_ids = {tag.id for tag in resolved_tags}

    existing_links = session.exec(
        select(WatchlistTags).where(WatchlistTags.watchlist_id == watchlist_id)
    ).all()

    existing_tag_ids = {link.tag_id for link in existing_links}

    # Remove links not present in incoming set
    for link in existing_links:
        if link.tag_id not in target_tag_ids:
            session.delete(link)

    # Add missing links
    for tag in resolved_tags:
        if tag.id not in existing_tag_ids:
            session.add(
                WatchlistTags(
                    watchlist_id=watchlist_id,
                    tag_id=tag.id,
                )
            )

    return resolved_tags


def get_tags_for_watchlist(
    session: Session,
    *,
    watchlist_id: int,
) -> list[Tags]:
    """
    Fetch all tags attached to a watchlist.
    """
    stmt = (
        select(Tags)
        .join(WatchlistTags, WatchlistTags.tag_id == Tags.id)
        .where(WatchlistTags.watchlist_id == watchlist_id)
        .order_by(Tags.name.asc())
    )
    return list(session.exec(stmt).all())


def get_tags_for_watchlists(
    session: Session,
    *,
    watchlist_ids: Sequence[int],
) -> dict[int, list[Tags]]:
    """
    Bulk load tags for many watchlists.

    Returns:
        {
            watchlist_id: [Tags, Tags, ...],
            ...
        }
    """
    if not watchlist_ids:
        return {}

    stmt = (
        select(WatchlistTags.watchlist_id, Tags)
        .join(Tags, Tags.id == WatchlistTags.tag_id)
        .where(WatchlistTags.watchlist_id.in_(watchlist_ids))
        .order_by(WatchlistTags.watchlist_id.asc(), Tags.name.asc())
    )

    rows = session.exec(stmt).all()

    result: dict[int, list[Tags]] = {watchlist_id: [] for watchlist_id in watchlist_ids}
    for watchlist_id, tag in rows:
        result.setdefault(watchlist_id, []).append(tag)

    return result


def search_tags(
    session,
    *,
    query: str,
    limit: int = 8,
) -> list[TagSearchOut]:
    rows = tag_crud.search_with_public_counts(
        session,
        query=query,
        limit=limit,
    )

    return [
        TagSearchOut(
            id=tag.id,
            name=tag.name,
            slug=tag.slug,
            category=tag.category,
            is_system=tag.is_system,
            created_at=tag.created_at,
            public_watchlist_count=public_watchlist_count,
        )
        for tag, public_watchlist_count in rows
    ]