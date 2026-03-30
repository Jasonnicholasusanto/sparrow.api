import json
from fastapi import APIRouter, Depends, HTTPException, status
import yfinance as yf

from app.api.dependencies.profile import get_current_profile
from app.schemas.stocks import TickerInfoResponse
from app.utils.global_variables import SECTOR_INDUSTRY_MAP


router = APIRouter(prefix="/industry", tags=["Industry"])


@router.get("/list")
async def get_sector_industry_list(
    user=Depends(get_current_profile),
):
    """
    Retrieve a list of market sectors.
    """
    return {"sector_industry_map": SECTOR_INDUSTRY_MAP}


@router.get("/info/{industry}")
async def get_industry_info(
    industry: str,
    user=Depends(get_current_profile),
):
    """
    Retrieve summary information for a given sector using Yahoo Finance.
    """

    industry = industry.lower()

    try:
        sector_data = yf.Industry(industry)
        response_data = {
            "sector": sector_data.name,
            "symbol": sector_data.symbol,
            "overview": sector_data.overview,
            "research_reports": sector_data.research_reports,
            "industry_info": TickerInfoResponse(**sector_data.ticker.info).model_dump(),
        }

        response_data = json.loads(json.dumps(response_data, default=str))
        return response_data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.get("/top-companies/{industry}")
async def get_industry_top_companies(
    industry: str, user=Depends(get_current_profile), limit: int = 25
):
    """
    Retrieve top companies in a given industry.
    """
    industry = industry.lower()

    try:
        industry_data = yf.Industry(industry)
        top_companies = industry_data.top_companies[:limit]
        top_growth_companies = industry_data.top_growth_companies[:limit]
        top_performing_companies = industry_data.top_performing_companies[:limit]

        response_data = {
            "industry": industry_data.name,
            "symbol": industry_data.symbol,
            "top_companies": top_companies.reset_index().to_dict(orient="records"),
            "top_growth_companies": top_growth_companies.reset_index().to_dict(
                orient="records"
            ),
            "top_performing_companies": top_performing_companies.reset_index().to_dict(
                orient="records"
            ),
        }

        response_data = json.loads(json.dumps(response_data, default=str))
        return response_data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )
