from fastapi import APIRouter

from app.api.routes import (
    auth,
    me,
    navbar,
    utils,
    users,
    watchlists,
    yfinance_main,
    favourite_stock,
    search_history,
    tags
)

api_router = APIRouter()
api_router.include_router(me.router)
api_router.include_router(users.router)
api_router.include_router(utils.router)
api_router.include_router(auth.router)
api_router.include_router(favourite_stock.router)
api_router.include_router(watchlists.router)
api_router.include_router(navbar.router)
api_router.include_router(search_history.router)
api_router.include_router(tags.router)
api_router.include_router(yfinance_main.router)
