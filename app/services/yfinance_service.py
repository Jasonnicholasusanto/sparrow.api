from __future__ import annotations

from typing import Any

import yfinance as yf

from app.schemas.stocks import SearchQuoteEnrichedResponse, TickerMarketSnapshotResponse
from app.utils.functions import safe_json_float


def build_ticker_market_snapshot(symbol: str, fi: dict[str, Any] | None) -> TickerMarketSnapshotResponse:
    fi = fi or {}

    last_price = safe_json_float(fi.get("lastPrice"))
    previous_close = safe_json_float(
        fi.get("regularMarketPreviousClose") or fi.get("previousClose")
    )

    regular_market_change = None
    regular_market_change_percent = None

    if (
        last_price is not None
        and previous_close is not None
        and previous_close != 0
    ):
        change = last_price - previous_close
        pct = (change / previous_close) * 100

        regular_market_change = safe_json_float(change)
        regular_market_change_percent = safe_json_float(pct)

    return TickerMarketSnapshotResponse(
        symbol=symbol.upper(),
        lastPrice=safe_json_float(last_price),
        currency=fi.get("currency"),
        previousClose=safe_json_float(previous_close),
        regularMarketChange=safe_json_float(regular_market_change),
        regularMarketChangePercent=safe_json_float(regular_market_change_percent),
    )

def fetch_ticker_market_snapshots(symbols: list[str]) -> dict[str, TickerMarketSnapshotResponse | None]:
    normalized_symbols = list(
        {
            symbol.strip().upper()
            for symbol in symbols
            if symbol and symbol.strip()
        }
    )

    if not normalized_symbols:
        return {}

    tickers_data = yf.Tickers(" ".join(normalized_symbols))
    results: dict[str, TickerMarketSnapshotResponse | None] = {}

    for symbol in normalized_symbols:
        try:
            raw_fi = tickers_data.tickers[symbol].fast_info
            fi = dict(raw_fi) if raw_fi else {}
            results[symbol] = build_ticker_market_snapshot(symbol, fi)
        except Exception:
            results[symbol] = None

    return results
