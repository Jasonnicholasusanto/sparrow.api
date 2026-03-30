from fastapi import APIRouter
from app.api.routes.yfinance_routes import industry, market, screen, sector, stocks

router = APIRouter(prefix="/yf", tags=["Yfinance Endpoints"])

router.include_router(stocks.router)
router.include_router(market.router)
router.include_router(screen.router)
router.include_router(sector.router)
router.include_router(industry.router)
