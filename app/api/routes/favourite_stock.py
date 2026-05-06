from fastapi import APIRouter, status, HTTPException
from fastapi import Depends

from app.api.dependencies.profile import get_current_profile
from app.api.deps import SessionDep
from app.schemas.favourite_stock import FavouriteStockCreate, FavouriteStockOut, FavouriteStockUpdate
from app.services import favourite_stock_service
from app.services.user_profile_service import get_user_profile_by_auth
import yfinance as yf


router = APIRouter(prefix="/favourite-stocks", tags=["Favourite Stocks"])


@router.post("/", response_model=FavouriteStockOut)
def add_favourite(
    payload: FavouriteStockCreate,
    db: SessionDep,
    user=Depends(get_current_profile),
):
    payload.symbol = payload.symbol.upper()

    existing = favourite_stock_service.get_favourite_stock_by_symbol(
        db, user_id=user.id, symbol=payload.symbol
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
    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"Invalid symbol '{payload.symbol}': {str(e)}"
        )

    return favourite_stock_service.add_favourite_stock(db, user.id, payload)


@router.delete("/{id}", response_model=FavouriteStockOut)
def remove_favourite(
    id: int,
    db: SessionDep,
    user=Depends(get_current_profile),
):
    return favourite_stock_service.remove_favourite_stock(db, user_id=user.id, id=id)


@router.delete("/", status_code=status.HTTP_200_OK, response_model=list[FavouriteStockOut])
def remove_all_favourites(
    db: SessionDep,
    user=Depends(get_current_profile),
):
    return favourite_stock_service.remove_all_favourite_stocks(db, user_id=user.id)


@router.patch("/{id}", response_model=FavouriteStockOut)
def update_favourite(
    id: int,
    payload: FavouriteStockUpdate,
    db: SessionDep,
    user=Depends(get_current_profile),
):
    return favourite_stock_service.update_favourite_stock(db, user.id, id, payload)


@router.get("/", response_model=list[FavouriteStockOut])
def list_favourites(
    db: SessionDep,
    user=Depends(get_current_profile),
):
    # 1. Get the list of favourite stocks for the user
    favourite_stocks = favourite_stock_service.list_favourite_stocks(db, user.id)

    if not favourite_stocks:
        return []
    
    # 2. For each favourite stock, fetch the latest ticker details
    enriched_favourites = favourite_stock_service.enrich_favourite_stocks_with_ticker_details(favourite_stocks)

    return enriched_favourites
