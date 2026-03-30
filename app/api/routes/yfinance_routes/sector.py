import json
from fastapi import APIRouter, Depends, HTTPException, status
import yfinance as yf
from app.api.dependencies.profile import get_current_profile
from app.schemas.stocks import TickerInfoResponse
from app.utils.global_variables import SECTOR_INDUSTRY_MAP


router = APIRouter(prefix="/sector", tags=["Sector"])


@router.get("/list")
async def get_sector_list(user=Depends(get_current_profile)):
    """
    Retrieve a list of market sectors.
    """
    return {"sector_industry_map": list(SECTOR_INDUSTRY_MAP.keys())}


@router.get("/{sector}/industries")
async def get_industries_by_sector(sector: str, user=Depends(get_current_profile)):
    """
    Retrieve a list of industries for a given sector.
    """
    sector = sector.lower()
    if sector not in SECTOR_INDUSTRY_MAP:
        return {
            "error": "Invalid sector. Valid sectors are: "
            + ", ".join(SECTOR_INDUSTRY_MAP.keys())
        }

    industries = SECTOR_INDUSTRY_MAP[sector]
    return {"sector": sector, "industries": industries}


@router.get("/info/{sector}")
async def get_sector_info(sector: str, user=Depends(get_current_profile)):
    """
    Retrieve summary information for a given sector using Yahoo Finance.
    """

    sector = sector.lower()
    if sector not in SECTOR_INDUSTRY_MAP:
        return {
            "error": "Invalid sector. Valid sectors are: "
            + ", ".join(SECTOR_INDUSTRY_MAP.keys())
        }

    try:
        sector_data = yf.Sector(sector)
        response_data = {
            "sector": sector_data.name,
            "symbol": sector_data.symbol,
            "overview": sector_data.overview,
            "research_reports": sector_data.research_reports,
            "sector_info": TickerInfoResponse(**sector_data.ticker.info).model_dump(),
        }

        response_data = json.loads(json.dumps(response_data, default=str))
        return response_data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.get("/top-companies/{sector}")
async def get_sector_top_companies(
    sector: str, user=Depends(get_current_profile), limit: int = 25
):
    """
    Retrieve top companies in a given sector using Yahoo Finance.
    """

    sector = sector.lower()
    if sector not in SECTOR_INDUSTRY_MAP:
        return {
            "error": "Invalid sector. Valid sectors are: "
            + ", ".join(SECTOR_INDUSTRY_MAP.keys())
        }

    try:
        sector_data = yf.Sector(sector)
        top_companies = sector_data.top_companies[:limit]
        response_data = {
            "sector": sector_data.name,
            "symbol": sector_data.symbol,
            "top_companies": top_companies.reset_index().to_dict(orient="records"),
        }

        response_data = json.loads(json.dumps(response_data, default=str))
        return response_data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.get("/top-etfs/{sector}")
async def get_sector_top_etfs(
    sector: str, user=Depends(get_current_profile), limit: int = 25
):
    """
    Retrieve top ETFs in a given sector using Yahoo Finance.
    """

    sector = sector.lower()
    if sector not in SECTOR_INDUSTRY_MAP:
        return {
            "error": "Invalid sector. Valid sectors are: "
            + ", ".join(SECTOR_INDUSTRY_MAP.keys())
        }

    try:
        sector_data = yf.Sector(sector)
        if len(sector_data.top_etfs) == 0:
            return {"error": f"No ETF data available for sector '{sector}'."}
        top_etfs_list = [
            {"symbol": symbol, "name": name}
            for symbol, name in list(sector_data.top_etfs.items())[:limit]
        ]
        response_data = {
            "sector": sector_data.name,
            "symbol": sector_data.symbol,
            "top_etfs": top_etfs_list,
        }

        response_data = json.loads(json.dumps(response_data, default=str))
        return response_data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.get("/top-mutual-funds/{sector}")
async def get_sector_top_mutual_funds(
    sector: str, user=Depends(get_current_profile), limit: int = 25
):
    """
    Retrieve top mutual funds in a given sector using Yahoo Finance.
    """

    sector = sector.lower()
    if sector not in SECTOR_INDUSTRY_MAP:
        return {
            "error": "Invalid sector. Valid sectors are: "
            + ", ".join(SECTOR_INDUSTRY_MAP.keys())
        }

    try:
        sector_data = yf.Sector(sector)
        if len(sector_data.top_mutual_funds) == 0:
            return {"error": f"No mutual fund data available for sector '{sector}'."}
        top_mutual_funds_list = [
            {"symbol": symbol, "name": name}
            for symbol, name in list(sector_data.top_mutual_funds.items())[:limit]
        ]
        response_data = {
            "sector": sector_data.name,
            "symbol": sector_data.symbol,
            "top_mutual_funds": top_mutual_funds_list,
        }

        response_data = json.loads(json.dumps(response_data, default=str))
        return response_data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )
