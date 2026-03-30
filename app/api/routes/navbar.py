from fastapi import APIRouter, Depends
from app.api.dependencies.profile import get_current_profile
from app.schemas.navbar_routes import NavbarRoutes
from app.api.deps import SessionDep
from app.services.navbar_routes_service import get_navbar_routes


router = APIRouter(prefix="/navbar", tags=["Navbar"])


@router.get("/items", response_model=NavbarRoutes)
async def get_navbar_items(
    db: SessionDep,
    user=Depends(get_current_profile),
):
    """
    Retrieve a list of navbar items.
    """
    result = get_navbar_routes(db)
    return result
