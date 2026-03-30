from fastapi import APIRouter, status, HTTPException
from fastapi import Depends

from app.api.dependencies.profile import get_current_profile
from app.api.deps import SessionDep
from app.models.favourite_stock import FavouriteStock
from app.schemas.favourite_stock import FavouriteStockCreate, FavouriteStockUpdate
from app.services import favourite_stock_service
from app.services.user_profile_service import get_user_profile_by_auth
import yfinance as yf


router = APIRouter(prefix="/favourite-stocks", tags=["Favourite Stocks"])


@router.post("/", response_model=FavouriteStock)
def add_favourite(
    payload: FavouriteStockCreate,
    db: SessionDep,
    user=Depends(get_current_profile),
):
    profile = get_user_profile_by_auth(db, auth_id=user.id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User profile not found.",
        )

    payload.symbol = payload.symbol.upper()

    existing = favourite_stock_service.get_favourite_stock_by_symbol(
        db, user_id=profile.id, symbol=payload.symbol
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Stock '{payload.symbol}' is already in your favourites list.",
        )

    try:
        ticker = yf.Ticker(payload.symbol)
        info = ticker.info
        payload.symbol = info.get("symbol", payload.symbol).upper()
        payload.exchange = info.get("exchange", "Unknown")
        payload.company_name = info.get("longName", "Unknown")
    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"Invalid symbol '{payload.symbol}': {str(e)}"
        )

    return favourite_stock_service.add_favourite_stock(db, profile.id, payload)


@router.delete("/{id}", response_model=FavouriteStock)
def remove_favourite(
    id: int,
    db: SessionDep,
    user=Depends(get_current_profile),
):
    profile = get_user_profile_by_auth(db, auth_id=user.id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User profile not found.",
        )
    return favourite_stock_service.remove_favourite_stock(db, id)


@router.patch("/{id}", response_model=FavouriteStock)
def update_favourite(
    id: int,
    payload: FavouriteStockUpdate,
    db: SessionDep,
    user=Depends(get_current_profile),
):
    profile = get_user_profile_by_auth(db, auth_id=user.id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User profile not found.",
        )
    return favourite_stock_service.update_favourite_stock(db, profile.id, id, payload)


@router.get("/", response_model=list[FavouriteStock])
def list_favourites(
    db: SessionDep,
    user=Depends(get_current_profile),
):
    profile = get_user_profile_by_auth(db, auth_id=user.id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User profile not found.",
        )
    return favourite_stock_service.list_favourite_stocks(db, profile.id)
