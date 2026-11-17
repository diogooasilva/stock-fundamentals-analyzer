from __future__ import annotations

from collections.abc import Mapping
from datetime import date
from math import isfinite
from typing import Any

from config.thresholds import METRIC_FORMATS


def to_number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        if isinstance(value, str):
            value = value.strip().replace(",", "")
            if not value or value.upper() in {"NA", "N/A", "NONE", "NULL", "NAN", "-"}:
                return None
        result = float(value)
        return result if isfinite(result) else None
    except (TypeError, ValueError):
        return None


def _mapping(data: Any) -> Mapping[str, Any]:
    return data if isinstance(data, Mapping) else {}


def _first_number(source: Mapping[str, Any], keys: tuple[str, ...] | list[str]) -> float | None:
    for key in keys:
        value = to_number(source.get(key))
        if value is not None:
            return value
    return None


def _dated_records(section: Mapping[str, Any], period_key: str) -> list[dict[str, Any]]:
    raw = section.get(period_key, {})
    records: list[dict[str, Any]] = []
    if isinstance(raw, dict):
        for date_key, values in raw.items():
            if isinstance(values, dict):
                record = dict(values)
                record.setdefault("date", date_key)
                records.append(record)
    elif isinstance(raw, list):
        records = [dict(x) for x in raw if isinstance(x, dict)]
    records.sort(key=lambda item: str(item.get("date") or item.get("filing_date") or ""), reverse=True)
    return records


def _statement(fundamentals: Mapping[str, Any], name: str, period: str) -> list[dict[str, Any]]:
    financials = _mapping(fundamentals.get("Financials"))
    section = _mapping(financials.get(name))
    if period == "TTM":
        # Yahoo can supply an already-aggregated trailing-twelve-month statement.
        # If unavailable, fall back to the latest four quarterly records.
        ttm_records = _dated_records(section, "ttm")
        if ttm_records:
            for record in ttm_records:
                record["_is_ttm_aggregate"] = True
            return ttm_records
        return _dated_records(section, "quarterly")
    return _dated_records(section, "yearly")


def _sum_last_four(records: list[dict[str, Any]], keys: tuple[str, ...]) -> float | None:
    if len(records) == 1 and records[0].get("_is_ttm_aggregate"):
        return _first_number(_mapping(records[0]), keys)
    if len(records) < 4:
        return None
    values = [_first_number(_mapping(record), keys) for record in records[:4]]
    if any(value is None for value in values):
        return None
    return sum(value for value in values if value is not None)


def _latest(records: list[dict[str, Any]]) -> dict[str, Any]:
    return records[0] if records else {}


def _previous_period(records: list[dict[str, Any]]) -> dict[str, Any]:
    return records[4] if len(records) >= 5 else {}


def _market_cap(fundamentals: Mapping[str, Any]) -> float | None:
    general = _mapping(fundamentals.get("General"))
    highlights = _mapping(fundamentals.get("Highlights"))
    value = _first_number(highlights, ("MarketCapitalization", "MarketCapitalizationMln"))
    if value is not None and highlights.get("MarketCapitalizationMln") is not None and highlights.get("MarketCapitalization") is None:
        value *= 1_000_000
    if value is None:
        value = _first_number(general, ("MarketCapitalization", "MarketCapitalizationMln"))
        if value is not None and general.get("MarketCapitalizationMln") is not None and general.get("MarketCapitalization") is None:
            value *= 1_000_000
    return value


def _enterprise_value(fundamentals: Mapping[str, Any], latest_bs: Mapping[str, Any]) -> float | None:
    valuation = _mapping(fundamentals.get("Valuation"))
    direct = _first_number(valuation, ("EnterpriseValue",))
    if direct is not None:
        return direct
    market_cap = _market_cap(fundamentals)
    debt = _first_number(latest_bs, ("totalDebt", "shortLongTermDebtTotal"))
    if debt is None:
        short_debt = _first_number(latest_bs, ("shortTermDebt", "shortLongTermDebt", "shortTermBorrowings")) or 0.0
        long_debt = _first_number(latest_bs, ("longTermDebt", "longTermDebtTotal", "longTermBorrowings")) or 0.0
        debt = short_debt + long_debt
    cash = _first_number(latest_bs, ("cash", "cashAndCashEquivalentsAtCarryingValue", "cashAndShortTermInvestments")) or 0.0
    if market_cap is None:
        return None
    return market_cap + debt - cash


def _free_cash_flow(records: list[dict[str, Any]], period: str) -> float | None:
    direct_key = ("freeCashFlow", "freeCashflow", "free_cash_flow")
    is_ttm_aggregate = period == "TTM" and len(records) == 1 and records[0].get("_is_ttm_aggregate")
    expected_count = 1 if period == "FY" or is_ttm_aggregate else 4
    source_records = records[:expected_count]
    direct_values = [_first_number(_mapping(record), direct_key) for record in source_records]
    if len(direct_values) >= expected_count and all(value is not None for value in direct_values):
        return sum(value for value in direct_values if value is not None)

    if len(source_records) < expected_count:
        return None
    cfo_values = [_first_number(_mapping(r), ("totalCashFromOperatingActivities", "operatingCashFlow", "cashFlowFromContinuingOperatingActivities")) for r in source_records]
    capex_values = [_first_number(_mapping(r), ("capitalExpenditures", "capitalExpenditure", "capex")) for r in source_records]
    if any(value is None for value in cfo_values) or any(value is None for value in capex_values):
        return None
    total = 0.0
    for cfo, capex in zip(cfo_values, capex_values):
        assert cfo is not None and capex is not None
        total += cfo + capex if capex < 0 else cfo - capex
    return total


def _eps_growth_cagr(fundamentals: Mapping[str, Any]) -> float | None:
    earnings = _mapping(fundamentals.get("Earnings"))
    annual = earnings.get("Annual", {})
    if isinstance(annual, dict):
        records = []
        for date_key, value in annual.items():
            if isinstance(value, dict):
                record = dict(value)
                record.setdefault("date", date_key)
                records.append(record)
    elif isinstance(annual, list):
        records = [dict(x) for x in annual if isinstance(x, dict)]
    else:
        records = []
    records.sort(key=lambda item: str(item.get("date", "")))
    if len(records) < 2:
        return None
    # Use the most recent four annual observations when available (a three-year CAGR).
    records = records[-4:]
    start = _first_number(records[0], ("epsActual", "eps", "reportedEPS"))
    end = _first_number(records[-1], ("epsActual", "eps", "reportedEPS"))
    if start is None or end is None or start <= 0 or end <= 0:
        return None
    first_date = str(records[0].get("date", ""))[:4]
    last_date = str(records[-1].get("date", ""))[:4]
    try:
        years = max(1, int(last_date) - int(first_date))
    except ValueError:
        years = len(records) - 1
    if years <= 0:
        return None
    return ((end / start) ** (1 / years) - 1) * 100.0


def _annual_avg_equity(balance_yearly: list[dict[str, Any]]) -> float | None:
    current = _first_number(_latest(balance_yearly), ("totalStockholderEquity", "totalStockholdersEquity", "totalShareholderEquity"))
    previous = _first_number(balance_yearly[1], ("totalStockholderEquity", "totalStockholdersEquity", "totalShareholderEquity")) if len(balance_yearly) > 1 else None
    if current is None:
        return None
    return (current + previous) / 2 if previous is not None else current


def _average_ttm_equity(balance_quarterly: list[dict[str, Any]]) -> float | None:
    current = _first_number(_latest(balance_quarterly), ("totalStockholderEquity", "totalStockholdersEquity", "totalShareholderEquity"))
    prior = _first_number(_previous_period(balance_quarterly), ("totalStockholderEquity", "totalStockholdersEquity", "totalShareholderEquity"))
    if current is None:
        return None
    return (current + prior) / 2 if prior is not None else current


def calculate_company_metrics(fundamentals: Mapping[str, Any], period: str) -> dict[str, float | None]:
    """Calculate the eight requested ratios for TTM or latest completed FY."""
    period = period.upper()
    if period not in {"TTM", "FY"}:
        raise ValueError("period must be 'TTM' or 'FY'")

    highlights = _mapping(fundamentals.get("Highlights"))
    valuation = _mapping(fundamentals.get("Valuation"))
    income = _statement(fundamentals, "Income_Statement", period)
    balance = _statement(fundamentals, "Balance_Sheet", period)
    cash_flow = _statement(fundamentals, "Cash_Flow", period)
    latest_bs = _latest(balance)
    if not latest_bs:
        # Some non-US issuers publish annual balance sheets more consistently than quarterly ones.
        fallback_balance = _statement(fundamentals, "Balance_Sheet", "FY")
        latest_bs = _latest(fallback_balance)
        if not balance:
            balance = fallback_balance
    market_cap = _market_cap(fundamentals)
    enterprise_value = _enterprise_value(fundamentals, latest_bs)

    if period == "TTM":
        revenue = _first_number(highlights, ("RevenueTTM",)) or _sum_last_four(income, ("totalRevenue", "revenue"))
        net_income = _sum_last_four(income, ("netIncome", "netIncomeApplicableToCommonShares", "netIncomeFromContinuingOperations"))
        ebitda = _sum_last_four(income, ("ebitda", "EBITDA"))
        cash_flow_fcf = _free_cash_flow(cash_flow, period)
        equity_average = _average_ttm_equity(balance)
        reported_pe = _first_number(valuation, ("TrailingPE",)) or _first_number(highlights, ("PERatio",))
        reported_ps = _first_number(valuation, ("PriceSalesTTM",))
        reported_peg = _first_number(highlights, ("PEGRatio",))
        reported_ev_ebitda = _first_number(valuation, ("EnterpriseValueEbitda",))
        reported_roe = _first_number(highlights, ("ReturnOnEquityTTM",))
    else:
        latest_income = _latest(income)
        revenue = _first_number(latest_income, ("totalRevenue", "revenue"))
        net_income = _first_number(latest_income, ("netIncome", "netIncomeApplicableToCommonShares", "netIncomeFromContinuingOperations"))
        ebitda = _first_number(latest_income, ("ebitda", "EBITDA"))
        cash_flow_fcf = _free_cash_flow(cash_flow, period)
        equity_average = _annual_avg_equity(balance)
        reported_pe = None
        reported_ps = None
        # PEG is normally based on forward growth estimates rather than a single
        # historical fiscal year, so Yahoo's current estimate-based PEG is shown
        # in both period tabs with its source/methodology disclosed in the UI.
        reported_peg = _first_number(highlights, ("PEGRatio",))
        reported_ev_ebitda = None
        reported_roe = None

    pe = reported_pe if period == "TTM" and reported_pe is not None else (market_cap / net_income if market_cap is not None and net_income not in (None, 0) else None)
    ps = reported_ps if period == "TTM" and reported_ps is not None else (market_cap / revenue if market_cap is not None and revenue not in (None, 0) else None)
    # PEG is a forward-looking estimate-based quote statistic. It is not a
    # historical FY ratio, so the latest Yahoo value is shown in either tab.
    peg = reported_peg

    short_debt = _first_number(latest_bs, ("shortTermDebt", "shortLongTermDebt", "shortTermBorrowings")) or 0.0
    long_debt = _first_number(latest_bs, ("longTermDebt", "longTermDebtTotal", "longTermBorrowings")) or 0.0
    total_debt = _first_number(latest_bs, ("totalDebt", "shortLongTermDebtTotal"))
    if total_debt is None:
        total_debt = short_debt + long_debt
    equity = _first_number(latest_bs, ("totalStockholderEquity", "totalStockholdersEquity", "totalShareholderEquity"))
    reported_de = _first_number(highlights, ("DebtToEquity",)) if period == "TTM" else None
    debt_to_equity = reported_de if reported_de is not None else (
        total_debt / equity if equity is not None and equity > 0 else None
    )

    roe = reported_roe if period == "TTM" and reported_roe is not None else (
        net_income / equity_average if net_income is not None and equity_average not in (None, 0) else None
    )
    p_fcf = market_cap / cash_flow_fcf if market_cap is not None and cash_flow_fcf not in (None, 0) else None
    ev_ebitda = reported_ev_ebitda if period == "TTM" and reported_ev_ebitda is not None else (
        enterprise_value / ebitda if enterprise_value is not None and ebitda not in (None, 0) else None
    )
    current_assets = _first_number(latest_bs, ("totalCurrentAssets", "currentAssets"))
    current_liabilities = _first_number(latest_bs, ("totalCurrentLiabilities", "currentLiabilities"))
    reported_current_ratio = _first_number(highlights, ("CurrentRatio",)) if period == "TTM" else None
    current_ratio = reported_current_ratio if reported_current_ratio is not None else (
        current_assets / current_liabilities
        if current_assets is not None and current_liabilities not in (None, 0)
        else None
    )

    # Avoid accidentally interpreting negative denominators as meaningful valuation multiples.
    if (net_income is not None and net_income <= 0) or (pe is not None and pe <= 0):
        pe = None
    if (revenue is not None and revenue <= 0) or (ps is not None and ps <= 0):
        ps = None
    if cash_flow_fcf is not None and cash_flow_fcf <= 0:
        p_fcf = None
    if ebitda is not None and ebitda <= 0:
        ev_ebitda = None

    return {
        "pe": pe,
        "ps": ps,
        "peg": peg,
        "de": debt_to_equity,
        "roe": roe,
        "p_fcf": p_fcf,
        "ev_ebitda": ev_ebitda,
        "cr": current_ratio,
    }


def format_metric_value(metric: str, value: float | None) -> str:
    if value is None:
        return "N/A"
    style = METRIC_FORMATS.get(metric, "multiple")
    if style == "percent":
        return f"{value * 100:,.1f}%"
    return f"{value:,.2f}x" if style == "multiple" else f"{value:,.2f}"
