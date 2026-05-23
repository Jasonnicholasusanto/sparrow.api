from __future__ import annotations

from typing import Any

import yfinance as yf
from app.schemas.watchlist_item import TickerMarketSnapshotResponse
from app.utils.functions import safe_json_float


def build_ticker_market_snapshot(fi: dict[str, Any] | None) -> TickerMarketSnapshotResponse:
    fi = fi or {}

    last_price = safe_json_float(fi.get("regularMarketPrice") or fi.get("currentPrice"))
    previous_close = safe_json_float(
        fi.get("regularMarketPreviousClose") or fi.get("previousClose")
    )
    volume = safe_json_float(fi.get("regularMarketVolume") or fi.get("volume"))
    regular_market_change = fi.get("regularMarketChange")
    regular_market_change_percent = fi.get("regularMarketChangePercent")

    return TickerMarketSnapshotResponse(
        ticker_name=fi.get("longName") or fi.get("shortName"),
        last_price=safe_json_float(last_price),
        currency=fi.get("currency"),
        previous_close=safe_json_float(previous_close),
        volume=safe_json_float(volume),
        regular_market_change=safe_json_float(regular_market_change),
        regular_market_change_percent=safe_json_float(regular_market_change_percent),
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
            info = tickers_data.tickers[symbol].info
            i = dict(info) if info else {}
            results[symbol] = build_ticker_market_snapshot(i)
        except Exception:
            results[symbol] = None

    return results
