"""Diagnostic test for Yahoo Finance data coverage across five companies.

Run with: python test_yahoo_data.py
No API key is required. This script only reads data and prints diagnostics.
"""

from __future__ import annotations

import math
import sys
import time
from typing import Any

import yfinance as yf

COMPANIES = {
    "Apple": "AAPL",
    "Microsoft": "MSFT",
    "Siemens": "SIE.DE",
    "Toyota": "7203.T",
    "Tencent": "0700.HK",
}

INFO_FIELDS = {
    "P/E (trailing)": "trailingPE",
    "Price-to-Sales (trailing)": "priceToSalesTrailing12Months",
    "PEG": "pegRatio",
    "Debt-to-Equity": "debtToEquity",
    "ROE": "returnOnEquity",
    "Price-to-Free-Cash-Flow": "priceToFreeCashflows",
    "EV/EBITDA": "enterpriseToEbitda",
    "Current Ratio": "currentRatio",
}

STATEMENTS = [
    ("Annual income statement", "income_stmt"),
    ("TTM income statement", "ttm_income_stmt"),
    ("Annual balance sheet", "balance_sheet"),
    ("Quarterly balance sheet", "quarterly_balance_sheet"),
    ("Annual cash-flow statement", "cashflow"),
    ("TTM cash-flow statement", "ttm_cashflow"),
]


def display_value(value: Any) -> str:
    if value is None:
        return "N/A"
    try:
        if isinstance(value, float) and math.isnan(value):
            return "N/A"
    except TypeError:
        pass
    if isinstance(value, (int, float)):
        return f"{value:,.4f}"
    return str(value)


def main() -> None:
    print("YAHOO FINANCE DATA COVERAGE TEST")
    print("=" * 72)
    print(f"Python: {sys.version.split()[0]}")
    print(f"yfinance: {getattr(yf, '__version__', 'unknown')}")
    print("No API key is used. Requests are made sequentially.\n")

    for company, symbol in COMPANIES.items():
        print("\n" + "#" * 72)
        print(f"{company} ({symbol})")
        print("#" * 72)
        ticker = yf.Ticker(symbol)

        try:
            info = ticker.get_info()
            if not isinstance(info, dict):
                info = {}
            print("Company:", info.get("longName") or info.get("shortName") or "Not returned")
            print("Exchange:", info.get("exchange", "Not returned"))
            print("Currency:", info.get("currency", "Not returned"))
            print("Sector:", info.get("sector", "Not returned"))
            print("Industry:", info.get("industry", "Not returned"))
            print("\nRatio fields from Yahoo's quote summary (where returned):")
            for label, key in INFO_FIELDS.items():
                print(f"  {label:30} {display_value(info.get(key))}")
        except Exception as exc:
            info = {}
            print(f"Company profile / info request failed: {type(exc).__name__}: {exc}")

        print("\nFinancial statement availability:")
        for label, attribute in STATEMENTS:
            try:
                frame = getattr(ticker, attribute)
                if frame is None or frame.empty:
                    print(f"  {label:30} NOT RETURNED")
                else:
                    periods = [str(col.date()) if hasattr(col, "date") else str(col) for col in frame.columns]
                    rows = list(frame.index)
                    print(f"  {label:30} OK | periods: {', '.join(periods[:4])}")
                    print("    Rows:", ", ".join(str(row) for row in rows[:12]))
            except Exception as exc:
                print(f"  {label:30} ERROR | {type(exc).__name__}: {exc}")

        # Avoid hammering Yahoo's endpoints when testing multiple symbols.
        time.sleep(2)

    print("\n" + "=" * 72)
    print("TEST COMPLETE")
    print("Please share the output, but do not include any private account information.")


if __name__ == "__main__":
    main()
