from datetime import datetime
from typing import Dict, List, Literal, Optional
from pydantic import BaseModel, Field, HttpUrl, AliasChoices


class TickersRequest(BaseModel):
    symbols: List[str]


class TickerItem(BaseModel):
    symbol: str
    start_date: str
    end_date: str
    interval: Literal[
        "1m",
        "2m",
        "5m",
        "15m",
        "30m",
        "60m",
        "90m",
        "1h",
        "1d",
        "5d",
        "1wk",
        "1mo",
        "3mo",
    ] = "1m"


class TickerFastInfoResponse(BaseModel):
    symbol: str = Field(..., description="Ticker symbol, e.g., AAPL or BHP.AX")
    currency: str = Field(..., description="Trading currency, e.g., USD or AUD")
    exchange: str = Field(..., description="Stock exchange, e.g., NASDAQ, ASX")
    quoteType: str = Field(
        ..., description="Type of instrument, e.g., EQUITY, ETF, INDEX, CRYPTO"
    )

    lastPrice: Optional[float] = Field(None, description="Most recent traded price")
    open: Optional[float] = Field(
        None, description="Opening price of the current session"
    )
    dayHigh: Optional[float] = Field(
        None, description="Highest price during today’s trading session"
    )
    dayLow: Optional[float] = Field(
        None, description="Lowest price during today’s trading session"
    )
    previousClose: Optional[float] = Field(
        None, description="Previous market session's closing price"
    )
    regularMarketPreviousClose: Optional[float] = Field(
        None, description="Regular market previous close (excludes after-hours)"
    )

    lastVolume: Optional[int] = Field(
        None, description="Latest recorded trading volume"
    )
    tenDayAverageVolume: Optional[int] = Field(
        None, description="Average daily volume over last 10 days"
    )
    threeMonthAverageVolume: Optional[int] = Field(
        None, description="Average daily volume over last 3 months"
    )

    marketCap: Optional[float] = Field(
        None, description="Market capitalization = price * shares outstanding"
    )
    shares: Optional[int] = Field(
        None, description="Total number of shares outstanding"
    )

    fiftyDayAverage: Optional[float] = Field(
        None, description="50-day moving average of closing prices"
    )
    twoHundredDayAverage: Optional[float] = Field(
        None, description="200-day moving average of closing prices"
    )

    yearChange: Optional[float] = Field(
        None, description="Percentage change over the past 12 months"
    )
    yearHigh: Optional[float] = Field(
        None, description="Highest price in the last 52 weeks"
    )
    yearLow: Optional[float] = Field(
        None, description="Lowest price in the last 52 weeks"
    )

    timezone: Optional[str] = Field(
        None, description="Exchange timezone, e.g., Australia/Sydney"
    )


class TickersFastInfoResponse(BaseModel):
    results: Dict[str, TickerFastInfoResponse]


class CompanyOfficer(BaseModel):
    name: Optional[str] = Field(None, description="Officer's full name")
    title: Optional[str] = Field(None, description="Job title or role")
    fiscalYear: Optional[int] = Field(
        None, description="Fiscal year of compensation data"
    )
    totalPay: Optional[float] = Field(
        None, description="Total compensation for the fiscal year"
    )
    exercisedValue: Optional[float] = Field(
        None, description="Value of exercised stock options"
    )
    unexercisedValue: Optional[float] = Field(
        None, description="Value of unexercised stock options"
    )


class TickerInfoResponse(BaseModel):
    # Company details
    address1: Optional[str] = Field(None, description="Primary company address line 1")
    address2: Optional[str] = Field(None, description="Primary company address line 2")
    city: Optional[str] = Field(None, description="City where company is located")
    state: Optional[str] = Field(None, description="State or region of the company")
    zip: Optional[str] = Field(None, description="Postal code")
    country: Optional[str] = Field(None, description="Country of headquarters")
    website: Optional[HttpUrl] = Field(None, description="Company website URL")
    industry: Optional[str] = Field(None, description="Industry classification")
    sector: Optional[str] = Field(None, description="Sector classification")
    longBusinessSummary: Optional[str] = Field(
        None, description="Detailed company business summary"
    )
    fullTimeEmployees: Optional[int] = Field(
        None, description="Number of full-time employees"
    )
    companyOfficers: Optional[List[CompanyOfficer]] = Field(
        None, description="List of company officers and their compensation"
    )

    # Market / price information
    previousClose: Optional[float] = Field(
        None, description="Previous trading day's closing price"
    )
    open: Optional[float] = Field(
        None, description="Opening price of the current trading day"
    )
    dayLow: Optional[float] = Field(None, description="Lowest price of the day")
    dayHigh: Optional[float] = Field(None, description="Highest price of the day")
    regularMarketPreviousClose: Optional[float] = Field(
        None, description="Previous close in regular trading session"
    )
    regularMarketOpen: Optional[float] = Field(
        None, description="Opening price in regular trading session"
    )
    regularMarketDayLow: Optional[float] = Field(
        None, description="Lowest price during regular session"
    )
    regularMarketDayHigh: Optional[float] = Field(
        None, description="Highest price during regular session"
    )
    regularMarketChange: Optional[float] = Field(
        None, description="Regular market price change"
    )
    regularMarketChangePercent: Optional[float] = Field(
        None, description="Regular market change percentage"
    )
    regularMarketTime: Optional[int] = Field(
        None, description="Epoch timestamp for regular market data"
    )
    preMarketChangePercent: Optional[float] = Field(
        None, description="Pre-market change percentage"
    )
    preMarketPrice: Optional[float] = Field(
        None, description="Pre-market trading price"
    )
    preMarketChange: Optional[float] = Field(
        None, description="Pre-market price change"
    )
    preMarketTime: Optional[int] = Field(
        None, description="Epoch timestamp for pre-market data"
    )
    postMarketChangePercent: Optional[float] = Field(
        None, description="After-hours change percentage"
    )
    postMarketPrice: Optional[float] = Field(
        None, description="After-hours trading price"
    )
    postMarketChange: Optional[float] = Field(
        None, description="After-hours price change"
    )
    postMarketTime: Optional[int] = Field(
        None, description="Epoch timestamp for after-hours data"
    )
    marketState: Optional[str] = Field(
        None, description="Current market state, e.g., REGULAR, PRE, POST, CLOSED"
    )

    # Key financial ratios and metrics
    dividendRate: Optional[float] = Field(
        None, description="Forward annual dividend rate"
    )
    dividendYield: Optional[float] = Field(
        None, description="Forward annual dividend yield - percentage"
    )
    exDividendDate: Optional[int] = Field(
        None, description="Ex-dividend date (epoch seconds)"
    )
    payoutRatio: Optional[float] = Field(None, description="Payout ratio - percentage")
    fiveYearAvgDividendYield: Optional[float] = Field(
        None, description="5-year average dividend yield"
    )
    trailingAnnualDividendRate: Optional[float] = Field(
        None, description="Trailing annual dividend rate"
    )
    trailingAnnualDividendYield: Optional[float] = Field(
        None, description="Trailing annual dividend yield - percentage"
    )
    beta: Optional[float] = Field(None, description="Stock beta (5Y monthly)")
    trailingPE: Optional[float] = Field(
        None, description="Trailing price-to-earnings ratio"
    )
    forwardPE: Optional[float] = Field(
        None, description="Forward price-to-earnings ratio"
    )
    volume: Optional[int] = Field(None, description="Trading volume")
    regularMarketVolume: Optional[int] = Field(
        None, description="Regular session trading volume"
    )
    averageVolume: Optional[int] = Field(
        None, description="Average trading volume (3 months)"
    )
    averageVolume10days: Optional[int] = Field(
        None, description="Average trading volume (10 days)"
    )
    averageDailyVolume10Day: Optional[int] = Field(
        None, description="Average daily trading volume (10 days)"
    )
    numberOfAnalystOpinions: Optional[int] = Field(
        None, description="Number of analyst opinions"
    )

    # Price and valuation data
    bid: Optional[float] = Field(None, description="Current bid price")
    ask: Optional[float] = Field(None, description="Current ask price")
    bidSize: Optional[int] = Field(None, description="Number of shares at bid price")
    askSize: Optional[int] = Field(None, description="Number of shares at ask price")
    marketCap: Optional[float] = Field(
        None, description="Market capitalization in local currency"
    )
    fiftyTwoWeekLow: Optional[float] = Field(None, description="52-week low")
    fiftyTwoWeekHigh: Optional[float] = Field(None, description="52-week high")
    allTimeHigh: Optional[float] = Field(
        None, description="All-time highest price recorded"
    )
    allTimeLow: Optional[float] = Field(
        None, description="All-time lowest price recorded"
    )
    fiftyDayAverage: Optional[float] = Field(None, description="50-day moving average")
    twoHundredDayAverage: Optional[float] = Field(
        None, description="200-day moving average"
    )
    currency: Optional[str] = Field(
        None, description="Trading currency symbol (e.g. AUD)"
    )
    enterpriseValue: Optional[float] = Field(None, description="Enterprise value")
    profitMargins: Optional[float] = Field(
        None, description="Profit margin - percentage"
    )
    floatShares: Optional[float] = Field(
        None,
        description="Floating shares - A float is a measure of the number of shares available for trading by the public. It is calculated by taking the number of issued and outstanding shares minus any restricted stock, which may not be publicly traded.",
    )
    sharesOutstanding: Optional[float] = Field(None, description="Shares outstanding")
    sharesShort: Optional[float] = Field(
        None, description="Number of shares sold short"
    )
    heldPercentInsiders: Optional[float] = Field(
        None, description="Percentage of shares held by insiders"
    )
    heldPercentInstitutions: Optional[float] = Field(
        None, description="Percentage of shares held by institutions"
    )
    impliedSharesOutstanding: Optional[float] = Field(
        None, description="Implied shares outstanding"
    )
    bookValue: Optional[float] = Field(None, description="Book value per share (MRQ)")
    priceToBook: Optional[float] = Field(None, description="Price-to-book ratio")
    lastFiscalYearEnd: Optional[int] = Field(
        None, description="Fiscal year ends (epoch seconds MRQ)"
    )
    nextFiscalYearEnd: Optional[int] = Field(
        None, description="Next fiscal year end (epoch seconds)"
    )
    mostRecentQuarter: Optional[int] = Field(
        None, description="Most recent quarter (epoch seconds MRQ)"
    )
    trailingEps: Optional[float] = Field(
        None, description="Trailing 12-month EPS (Diluted EPS - TTM)"
    )
    forwardEps: Optional[float] = Field(None, description="Forward EPS estimate")
    earningsQuarterlyGrowth: Optional[float] = Field(
        None, description="Quarterly earnings growth - percentage (Year-on-year)"
    )
    lastSplitFactor: Optional[str] = Field(
        None, description="Last split factor (e.g. 1:1)"
    )
    lastSplitDate: Optional[int] = Field(
        None, description="Last split date (epoch seconds)"
    )
    fiftyTwoWeekChangePercent: Optional[float] = Field(
        None, description="52-week change - percentage"
    )
    SandP52WeekChange: Optional[float] = Field(
        None, description="S&P 500 52-week change - percentage"
    )
    currentPrice: Optional[float] = Field(None, description="Current trading price")
    targetHighPrice: Optional[float] = Field(
        None, description="Analyst high target price"
    )
    targetLowPrice: Optional[float] = Field(
        None, description="Analyst low target price"
    )
    targetMeanPrice: Optional[float] = Field(
        None, description="Analyst mean target price"
    )
    targetMedianPrice: Optional[float] = Field(
        None, description="Analyst median target price"
    )
    recommendationMean: Optional[float] = Field(
        None, description="Analyst recommendation mean value"
    )
    recommendationKey: Optional[str] = Field(
        None, description="Analyst recommendation summary (e.g., buy, hold, sell)"
    )

    # Financial metrics
    totalCash: Optional[float] = Field(None, description="Total cash (MRQ)")
    totalCashPerShare: Optional[float] = Field(
        None, description="Total cash per share (MRQ)"
    )
    ebitda: Optional[float] = Field(
        None,
        description="Earnings Before Interest, Taxes, Depreciation, and Amortization (EBITDA)",
    )
    totalDebt: Optional[float] = Field(None, description="Total debt (MRQ)")
    currentRatio: Optional[float] = Field(None, description="Current ratio (MRQ)")
    totalRevenue: Optional[float] = Field(None, description="Total revenue (TTM)")
    debtToEquity: Optional[float] = Field(
        None, description="Total debt/equity - percentage (MRQ)"
    )
    revenuePerShare: Optional[float] = Field(
        None, description="Revenue per share (TTM)"
    )
    revenueGrowth: Optional[float] = Field(
        None, description="Quarterly revenue growth - percentage (Year-on-year)"
    )
    returnOnAssets: Optional[float] = Field(
        None, description="Return on assets (ROA) - percentage (TTM)"
    )
    returnOnEquity: Optional[float] = Field(
        None, description="Return on equity (ROE) - percentage(TTM)"
    )
    grossProfits: Optional[float] = Field(None, description="Gross profit (TTM)")
    operatingMargins: Optional[float] = Field(
        None, description="Operating margin - percentage (TTM)"
    )
    operatingCashflow: Optional[float] = Field(
        None, description="Operating cash flow (TTM)"
    )
    freeCashflow: Optional[float] = Field(
        None, description="Levered free cash flow (TTM)"
    )
    financialCurrency: Optional[str] = Field(
        None, description="Currency used in financial statements"
    )

    # Quote / exchange metadata
    symbol: Optional[str] = Field(None, description="Ticker symbol")
    language: Optional[str] = Field(
        None, description="Language of the report (e.g., en-US)"
    )
    region: Optional[str] = Field(None, description="Region (e.g., US, AU)")
    typeDisp: Optional[str] = Field(None, description="Type of security (e.g., Equity)")
    quoteSourceName: Optional[str] = Field(None, description="Quote source name")
    longName: Optional[str] = Field(None, description="Full company name")
    shortName: Optional[str] = Field(None, description="Short company name")
    regularMarketTime: Optional[int] = Field(
        None, description="Timestamp of last regular market trade"
    )
    exchange: Optional[str] = Field(None, description="Exchange symbol (e.g., ASX)")
    exchangeTimezoneName: Optional[str] = Field(
        None, description="Exchange timezone name (e.g., Australia/Sydney)"
    )
    exchangeTimezoneShortName: Optional[str] = Field(
        None, description="Exchange timezone short code (e.g., AEDT)"
    )
    market: Optional[str] = Field(
        None, description="Market identifier (e.g., au_market)"
    )
    regularMarketChangePercent: Optional[float] = Field(
        None, description="Percent change during regular market session"
    )
    regularMarketDayRange: Optional[str] = Field(None, description="Day trading range")
    fullExchangeName: Optional[str] = Field(
        None, description="Full name of the exchange"
    )
    averageDailyVolume3Month: Optional[int] = Field(
        None, description="Average daily trading volume over 3 months"
    )
    fiftyTwoWeekLowChange: Optional[float] = Field(
        None, description="Change from 52-week low"
    )
    fiftyTwoWeekLowChangePercent: Optional[float] = Field(
        None, description="Percent change from 52-week low"
    )
    fiftyTwoWeekRange: Optional[str] = Field(None, description="52-week price range")
    fiftyTwoWeekHighChange: Optional[float] = Field(
        None, description="Change from 52-week high"
    )
    fiftyTwoWeekHighChangePercent: Optional[float] = Field(
        None, description="Percent change from 52-week high"
    )
    earningsTimestamp: Optional[int] = Field(
        None, description="Most recent earnings report timestamp"
    )
    epsTrailingTwelveMonths: Optional[float] = Field(
        None, description="Trailing twelve-month EPS"
    )
    epsForward: Optional[float] = Field(None, description="Forward EPS estimate")
    epsCurrentYear: Optional[float] = Field(
        None, description="EPS estimate for the current fiscal year"
    )
    priceEpsCurrentYear: Optional[float] = Field(
        None, description="Price-to-EPS ratio for the current year"
    )
    exchangeDataDelayedBy: Optional[int] = Field(
        None, description="Exchange data delay (in seconds)"
    )
    averageAnalystRating: Optional[str] = Field(
        None, description="Average analyst rating string (e.g., 2.2 - Buy)"
    )
    regularMarketPrice: Optional[float] = Field(
        None, description="Last regular market price"
    )


class SearchResponse(BaseModel):
    symbol: Optional[str] = Field(None, description="Ticker symbol")
    score: Optional[float] = Field(None, description="Relevance score")
    shortname: Optional[str] = Field(None, description="Short name of the company")
    longname: Optional[str] = Field(None, description="Long name of the company")
    index: Optional[str] = Field(None, description="Index type if applicable")
    exchange: Optional[str] = Field(None, description="Exchange symbol")
    exchDisp: Optional[str] = Field(None, description="Exchange where listed")
    quoteType: Optional[str] = Field(None, description="Type of quote (e.g., EQUITY)")
    typeDisp: Optional[str] = Field(None, description="Display type of the instrument")
    sector: Optional[str] = Field(None, description="Sector of the company")
    sectorDisp: Optional[str] = Field(None, description="Display sector of the company")
    industry: Optional[str] = Field(None, description="Industry of the company")
    industryDisp: Optional[str] = Field(
        None, description="Display industry of the company"
    )


class TickerHistory(BaseModel):
    timestamp: datetime = Field(
        ...,
        validation_alias=AliasChoices("Date", "Datetime"),
        serialization_alias="timestamp",
    )
    open: float = Field(..., validation_alias="Open", serialization_alias="open")
    high: float = Field(..., validation_alias="High", serialization_alias="high")
    low: float = Field(..., validation_alias="Low", serialization_alias="low")
    close: float = Field(..., validation_alias="Close", serialization_alias="close")
    volume: int = Field(..., validation_alias="Volume", serialization_alias="volume")
    dividends: float = Field(
        ..., validation_alias="Dividends", serialization_alias="dividends"
    )
    stock_splits: float = Field(
        ..., validation_alias="Stock Splits", serialization_alias="stock_splits"
    )


class SparklinePoint(BaseModel):
    timestamp: str
    close: float


class TickerSparklineResponse(BaseModel):
    symbol: str
    points: List[SparklinePoint] = Field(default_factory=list)


class MultiTickerSparklineResponse(BaseModel):
    period: str
    interval: str
    results: List[TickerSparklineResponse] = Field(default_factory=list)