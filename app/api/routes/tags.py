from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.dependencies.profile import get_current_profile
from app.api.deps import SessionDep
from app.schemas.tags import TagSearchOut
from app.services.tags import search_tags


router = APIRouter(prefix="/tags", tags=["Tags"])

@router.get("/search", response_model=list[TagSearchOut])
def search_tags_route(
    db: SessionDep,
    user=Depends(get_current_profile),
    q: str = Query(..., min_length=1, max_length=50),
    limit: int = Query(8, ge=1, le=20),
):
    """
    Search tags by name/slug.
    Returns matching tags with optional public watchlist count.
    """
    try:
        return search_tags(
            session=db,
            query=q,
            limit=limit,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search tags: {str(e)}",
        )