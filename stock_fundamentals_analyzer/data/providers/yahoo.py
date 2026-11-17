from __future__ import annotations

from math import isfinite
from typing import Any

import pandas as pd


class ProviderError(RuntimeError):
    """Raised when Yahoo Finance cannot provide usable company data."""


def _clean_number(value: Any) -> float | None:
    """Convert Yahoo/pandas values to finite floats without leaking NaN/NA."""
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if isfinite(number) else None


def _normalise_label(value: Any) -> str:
    return "".join(ch.lower() for ch in str(value) if ch.isalnum())


# Yahoo has changed some statement labels over time. The adapter maps several
# known variants into the stable keys expected by calculations/ratios.py.
STATEMENT_ROWS: dict[str, dict[str, tuple[str, ...]]] = {
    "income": {
        "totalRevenue": ("Total Revenue", "Operating Revenue", "Revenue"),
        "netIncome": (
            "Net Income",
            "Net Income Common Stockholders",
            "Net Income From Continuing Operation Net Minority Interest",
            "Net Income From Continuing And Discontinued Operation",
            "Net Income From Continuing Operations",
        ),
        "ebitda": ("EBITDA", "Normalized EBITDA"),
    },
    "balance": {
        "totalCurrentAssets": ("Current Assets", "Total Current Assets"),
        "totalCurrentLiabilities": ("Current Liabilities", "Total Current Liabilities"),
        "totalStockholderEquity": (
            "Stockholders Equity",
            "Common Stock Equity",
            "Total Stockholder Equity",
            "Total Equity Gross Minority Interest",
        ),
        "totalDebt": ("Total Debt", "Total Debt And Capital Lease Obligation"),
        "shortTermDebt": ("Current Debt", "Short Term Debt", "Current Debt And Lease Obligation"),
        "longTermDebt": ("Long Term Debt", "Long Term Debt And Capital Lease Obligation"),
        "cash": (
            "Cash And Cash Equivalents",
            "Cash Cash Equivalents And Short Term Investments",
            "Cash And Short Term Investments",
        ),
    },
    "cashflow": {
        "freeCashFlow": ("Free Cash Flow", "FreeCashFlow"),
        "operatingCashFlow": (
            "Operating Cash Flow",
            "Cash Flow From Continuing Operating Activities",
            "Total Cash From Operating Activities",
        ),
        "capitalExpenditures": ("Capital Expenditure", "Capital Expenditures", "Capital Expenditure Reported"),
    },
}


def _frame_records(frame: Any, statement_type: str, *, ttm_aggregate: bool = False) -> list[dict[str, Any]]:
    """Convert a yfinance statement DataFrame into dated, normalised records."""
    if not isinstance(frame, pd.DataFrame) or frame.empty:
        return []

    mapping = STATEMENT_ROWS[statement_type]
    row_index = {_normalise_label(label): label for label in frame.index}
    records: list[dict[str, Any]] = []

    for column in frame.columns:
        record: dict[str, Any] = {}
        try:
            timestamp = pd.Timestamp(column)
            record["date"] = timestamp.date().isoformat()
        except Exception:
            record["date"] = str(column)

        for output_key, candidates in mapping.items():
            value = None
            for candidate in candidates:
                actual_label = row_index.get(_normalise_label(candidate))
                if actual_label is not None:
                    value = _clean_number(frame.at[actual_label, column])
                    if value is not None:
                        break
            if value is not None:
                record[output_key] = value

        if ttm_aggregate:
            record["_is_ttm_aggregate"] = True
        records.append(record)

    records.sort(key=lambda item: str(item.get("date", "")), reverse=True)
    return records


def _safe_attribute(ticker: Any, names: tuple[str, ...]) -> Any:
    for name in names:
        try:
            value = getattr(ticker, name)
        except Exception:
            continue
        if value is not None:
            return value
    return None


def _number_from_info(info: dict[str, Any], *keys: str) -> float | None:
    for key in keys:
        value = _clean_number(info.get(key))
        if value is not None:
            return value
    return None


class YahooFinanceProvider:
    """Yahoo Finance adapter returning a provider-neutral fundamentals structure.

    Yahoo's public data endpoints do not require an API key. This adapter uses
    yfinance and deliberately normalises statement labels before calculations.
    """

    def __init__(self) -> None:
        try:
            import yfinance as yf
        except ImportError as exc:  # pragma: no cover - depends on installation
            raise ProviderError("yfinance is not installed. Run: python -m pip install yfinance") from exc
        self.yf = yf

    def search_companies(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        query = query.strip()
        if not query:
            return []
        try:
            search = self.yf.Search(
                query,
                max_results=max(1, min(int(limit), 25)),
                news_count=0,
                lists_count=0,
                include_cb=False,
                include_nav_links=False,
                raise_errors=True,
            )
            quotes = search.quotes or []
        except Exception as exc:
            raise ProviderError(f"Yahoo Finance company search failed: {exc}") from exc

        results: list[dict[str, Any]] = []
        for quote in quotes:
            if not isinstance(quote, dict):
                continue
            symbol = str(quote.get("symbol") or "").strip()
            quote_type = str(quote.get("quoteType") or "").upper()
            if not symbol or (quote_type and quote_type not in {"EQUITY", "COMMON STOCK"}):
                continue
            results.append(
                {
                    "Symbol": symbol,
                    "Code": symbol,
                    "Exchange": quote.get("exchange") or quote.get("exchDisp") or "",
                    "Name": quote.get("longname") or quote.get("shortname") or symbol,
                    "Country": quote.get("region") or quote.get("country") or "",
                    "Currency": quote.get("currency") or "",
                    "Type": quote_type or "EQUITY",
                }
            )
        return results

    def get_industry_companies(self, industry_key: str, region: str = "US", limit: int = 20) -> list[dict[str, Any]]:
        """Return Yahoo Finance's top-company sample for a Yahoo industry key.

        Yahoo's Industry endpoint returns a top-company list, not a complete
        industry census. Callers must label derived statistics as sample-based.
        """
        key = str(industry_key or "").strip()
        if not key:
            return []
        try:
            industry_class = getattr(self.yf, "Industry", None)
            if industry_class is None:
                return []
            industry = industry_class(key, region=(region or "US").upper())
            frame = getattr(industry, "top_companies", None)
            source_name = "top companies"
            if not isinstance(frame, pd.DataFrame) or frame.empty:
                frame = getattr(industry, "top_performing_companies", None)
                source_name = "top performing companies"
            if not isinstance(frame, pd.DataFrame) or frame.empty:
                frame = getattr(industry, "top_growth_companies", None)
                source_name = "top growth companies"
            if not isinstance(frame, pd.DataFrame) or frame.empty:
                return []
            rows: list[dict[str, Any]] = []
            for index, row in frame.head(max(1, min(int(limit), 30))).iterrows():
                symbol = row.get("symbol", row.get("ticker", row.get("Symbol", index)))
                if symbol is None:
                    continue
                symbol = str(symbol).strip()
                if not symbol or symbol.lower() == "nan":
                    continue
                rows.append({
                    "Symbol": symbol,
                    "Name": str(row.get("name", row.get("shortName", symbol))),
                    "Source": source_name,
                })
            return rows
        except Exception as exc:
            raise ProviderError(f"Yahoo Finance industry lookup failed for '{key}': {exc}") from exc

    def get_price_history(self, symbol: str, period: str = "1y", interval: str = "1d") -> list[dict[str, Any]]:
        """Return historical OHLCV rows in a serialisable form."""
        symbol = symbol.strip().upper()
        try:
            frame = self.yf.Ticker(symbol).history(period=period, interval=interval, auto_adjust=False)
        except Exception as exc:
            raise ProviderError(f"Yahoo Finance price history failed for {symbol}: {exc}") from exc
        if not isinstance(frame, pd.DataFrame) or frame.empty:
            return []
        result: list[dict[str, Any]] = []
        for index, row in frame.iterrows():
            try:
                result.append({
                    "date": pd.Timestamp(index).date().isoformat(),
                    "open": _clean_number(row.get("Open")),
                    "high": _clean_number(row.get("High")),
                    "low": _clean_number(row.get("Low")),
                    "close": _clean_number(row.get("Close")),
                    "volume": _clean_number(row.get("Volume")),
                })
            except Exception:
                continue
        return result

    def get_fundamentals(self, symbol: str) -> dict[str, Any]:
        symbol = symbol.strip().upper()
        if not symbol:
            raise ProviderError("Enter a Yahoo Finance ticker symbol.")

        try:
            ticker = self.yf.Ticker(symbol)
        except Exception as exc:
            raise ProviderError(f"Could not initialise Yahoo Finance ticker {symbol}: {exc}") from exc

        try:
            info = ticker.info or {}
        except Exception:
            info = {}
        if not isinstance(info, dict):
            info = {}

        income_annual = _frame_records(_safe_attribute(ticker, ("income_stmt", "financials")), "income")
        income_quarterly = _frame_records(_safe_attribute(ticker, ("quarterly_income_stmt", "quarterly_financials")), "income")
        income_ttm = _frame_records(_safe_attribute(ticker, ("ttm_income_stmt",)), "income", ttm_aggregate=True)

        balance_annual = _frame_records(_safe_attribute(ticker, ("balance_sheet", "balancesheet")), "balance")
        balance_quarterly = _frame_records(_safe_attribute(ticker, ("quarterly_balance_sheet", "quarterly_balancesheet")), "balance")

        cash_annual = _frame_records(_safe_attribute(ticker, ("cashflow", "cash_flow")), "cashflow")
        cash_quarterly = _frame_records(_safe_attribute(ticker, ("quarterly_cashflow", "quarterly_cash_flow")), "cashflow")
        cash_ttm = _frame_records(_safe_attribute(ticker, ("ttm_cashflow", "ttm_cash_flow")), "cashflow", ttm_aggregate=True)

        if not info and not any((income_annual, income_quarterly, income_ttm, balance_annual, cash_annual)):
            raise ProviderError(
                f"Yahoo Finance returned no company profile or financial statements for {symbol}. "
                "Check the ticker symbol and try again later."
            )

        market_cap = _number_from_info(info, "marketCap")
        enterprise_value = _number_from_info(info, "enterpriseValue")
        peg = _number_from_info(info, "pegRatio", "trailingPegRatio")
        reported_de = _number_from_info(info, "debtToEquity")
        # Yahoo reports Debt/Equity as a percentage; the app stores it as a ratio multiple.
        de_ratio = reported_de / 100.0 if reported_de is not None else None

        general = {
            "Name": info.get("longName") or info.get("shortName") or symbol,
            "Code": symbol,
            "PrimaryTicker": symbol,
            "Exchange": info.get("exchange") or info.get("fullExchangeName") or "",
            "CountryName": info.get("country") or info.get("region") or "",
            "CurrencyCode": info.get("currency") or "",
            "Sector": info.get("sector") or "",
            "Industry": info.get("industry") or "",
            "IndustryKey": info.get("industryKey") or "",
            "SectorKey": info.get("sectorKey") or "",
            "ISIN": info.get("isin") or "",
        }
        highlights = {
            "MarketCapitalization": market_cap,
            "CurrentPrice": _number_from_info(info, "currentPrice", "regularMarketPrice"),
            "PreviousClose": _number_from_info(info, "previousClose", "regularMarketPreviousClose"),
            "FiftyTwoWeekHigh": _number_from_info(info, "fiftyTwoWeekHigh"),
            "FiftyTwoWeekLow": _number_from_info(info, "fiftyTwoWeekLow"),
            "FiftyTwoWeekChange": _number_from_info(info, "52WeekChange"),
            "PERatio": _number_from_info(info, "trailingPE"),
            "PEGRatio": peg,
            "ReturnOnEquityTTM": _number_from_info(info, "returnOnEquity"),
            "DebtToEquity": de_ratio,
            "CurrentRatio": _number_from_info(info, "currentRatio"),
            "RevenueTTM": _number_from_info(info, "totalRevenue"),
        }
        valuation = {
            "EnterpriseValue": enterprise_value,
            "TrailingPE": _number_from_info(info, "trailingPE"),
            "PriceSalesTTM": _number_from_info(info, "priceToSalesTrailing12Months"),
            "EnterpriseValueEbitda": _number_from_info(info, "enterpriseToEbitda"),
        }
        financials = {
            "Income_Statement": {
                "yearly": income_annual,
                "quarterly": income_quarterly,
                "ttm": income_ttm,
            },
            "Balance_Sheet": {"yearly": balance_annual, "quarterly": balance_quarterly},
            "Cash_Flow": {
                "yearly": cash_annual,
                "quarterly": cash_quarterly,
                "ttm": cash_ttm,
            },
        }
        return {
            "General": general,
            "Highlights": highlights,
            "Valuation": valuation,
            "Financials": financials,
            "Provider": "Yahoo Finance via yfinance",
            "Symbol": symbol,
        }
