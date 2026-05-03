from typing import Optional, List
from sqlmodel import select, Session
from app.models.favourite_stock import FavouriteStock
from app.schemas.favourite_stock import FavouriteStockCreate, FavouriteStockUpdate
from app.crud.base import CRUDBase


class CRUDFavouriteStock(
    CRUDBase[FavouriteStock, FavouriteStockCreate, FavouriteStockUpdate]
):
    def get_by_id(self, db: Session, *, id: int) -> Optional[FavouriteStock]:
        statement = select(FavouriteStock).where(FavouriteStock.id == id)
        return db.exec(statement).first()
    
    def get_by_user_and_id(self, db: Session, *, user_id: str, id: int) -> Optional[FavouriteStock]:
        statement = select(FavouriteStock).where(
            FavouriteStock.user_id == user_id, FavouriteStock.id == id
        )
        return db.exec(statement).first()

    def get_by_symbol(
        self, db: Session, *, user_id: str, symbol: str
    ) -> Optional[FavouriteStock]:
        statement = select(FavouriteStock).where(
            FavouriteStock.user_id == user_id, FavouriteStock.symbol == symbol
        )
        return db.exec(statement).first()

    def get_all_by_user(self, db: Session, *, user_id: str) -> List[FavouriteStock]:
        statement = select(FavouriteStock).where(FavouriteStock.user_id == user_id)
        return db.exec(statement).all()


favourite_stock = CRUDFavouriteStock(FavouriteStock)
