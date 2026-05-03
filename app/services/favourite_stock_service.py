import uuid

from fastapi import HTTPException, status
from sqlmodel import Session
from app.schemas.favourite_stock import FavouriteStockCreate, FavouriteStockOut, FavouriteStockUpdate
from app.crud.favourite_stock import favourite_stock as crud_favourite_stock
from app.services.yfinance_service import fetch_ticker_market_snapshots


def get_favourite_stock_by_symbol(session: Session, user_id: uuid.UUID, symbol: str):
    return crud_favourite_stock.get_by_symbol(session, user_id=user_id, symbol=symbol)


def list_favourite_stocks(session: Session, user_id: uuid.UUID) -> list[FavouriteStockOut]:
    favourites = crud_favourite_stock.get_all_by_user(session, user_id=user_id)

    return [
        FavouriteStockOut.model_validate(favourite, from_attributes=True)
        for favourite in favourites
    ]


def add_favourite_stock(session: Session, user_id: uuid.UUID, payload: FavouriteStockCreate):
    existing = crud_favourite_stock.get_by_symbol(
        session, user_id=user_id, symbol=payload.symbol
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Stock already in favourites list.",
        )

    new_item = crud_favourite_stock.create(
        session=session,
        obj_in=payload,
        user_id=user_id,
    )
    return new_item


def remove_favourite_stock(
    session: Session,
    user_id: uuid.UUID,
    id: int,
):
    stock = crud_favourite_stock.get_by_user_and_id(session, user_id=user_id, id=id)
    if not stock:
        raise HTTPException(status_code=404, detail="Favourite stock not found.")

    deleted_stock = crud_favourite_stock.remove(session, id=stock.id)
    return FavouriteStockOut.model_validate(deleted_stock, from_attributes=True)


def update_favourite_stock(
    session: Session, user_id: uuid.UUID, id: int, data: FavouriteStockUpdate
):
    stock = crud_favourite_stock.get_by_user_and_id(session, user_id=user_id, id=id)
    if not stock:
        raise HTTPException(status_code=404, detail="Favourite stock not found.")

    updated = crud_favourite_stock.update(session=session, id=id, obj_in=data)
    return FavouriteStockOut.model_validate(updated, from_attributes=True)


def enrich_favourite_stock_with_ticker_details(favourite_stocks: list[FavouriteStockOut]) -> list[FavouriteStockOut]:
    symbols = [
        favourite.symbol for favourite in favourite_stocks if favourite.symbol
    ]

    snapshot_map = fetch_ticker_market_snapshots(symbols)

    for favourite in favourite_stocks:
        if favourite.symbol in snapshot_map:
            snapshot = snapshot_map[favourite.symbol]
            favourite.ticker_details = snapshot

    return favourite_stocks
