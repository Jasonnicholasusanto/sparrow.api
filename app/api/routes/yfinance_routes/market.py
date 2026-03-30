from datetime import datetime, tzinfo
import json
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
import yfinance as yf

from app.api.dependencies.profile import get_current_profile
from app.utils.global_variables import MARKETS


router = APIRouter(prefix="/market", tags=["Market"])


def safe_json(obj: Any):
    """Recursively convert complex types (datetime, tzinfo, etc.) to JSON-serializable forms."""
    if isinstance(obj, dict):
        return {k: safe_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [safe_json(v) for v in obj]
    elif isinstance(obj, (datetime,)):
        return obj.isoformat()
    elif isinstance(obj, tzinfo):
        return str(obj)
    elif hasattr(obj, "__dict__"):
        return {k: safe_json(v) for k, v in vars(obj).items()}
    else:
        return obj


@router.get("/yf/info/{market_indicator}")
async def get_market_info(market_indicator: str, user=Depends(get_current_profile)):
    """
    Get the current status of a market (open/closed).

    Args:
        market (str): The market to check (e.g., 'US', 'ASIA').

    Returns:
        dict: A dictionary containing the market status.
    """
    market_indicator = market_indicator.upper()
    if market_indicator not in MARKETS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid market. Supported markets are: " + ", ".join(MARKETS),
        )

    try:
        market = yf.Market(market_indicator)
        market_data = market.summary

        response_data = {
            "market": market_indicator,
            "info": market_data,
        }

        response_data = json.loads(json.dumps(response_data, default=str))
        return response_data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.get("/yf/status/{market_indicator}")
async def get_market_status(market_indicator: str, user=Depends(get_current_profile)):
    """
    Fetch current market status using Yahoo Finance's Market API.

    Example:
        /api/v1/market/yf/status/US
        /api/v1/market/yf/status/ASIA
    """
    market_indicator = market_indicator.upper()

    # Optional validation
    if "MARKETS" in globals() and market_indicator not in MARKETS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid market. Supported markets: {', '.join(MARKETS.keys())}",
        )

    try:
        market_obj = yf.Market(market_indicator)
        market_status = market_obj.status
        serializable_status = safe_json(market_status)

        return {
            "market": market_indicator,
            "status": serializable_status.get("status", "unknown"),
            "details": serializable_status,
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch market status: {str(e)}",
        )
