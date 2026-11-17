from __future__ import annotations

from pathlib import Path

import pandas as pd


def load_peer_groups(path: Path) -> dict[str, list[str]]:
    """Read optional industry,ticker mappings from a CSV file."""
    if not path.exists():
        return {}
    try:
        frame = pd.read_csv(path)
    except (OSError, pd.errors.ParserError, UnicodeDecodeError):
        return {}
    if not {"industry", "ticker"}.issubset(frame.columns):
        return {}
    result: dict[str, list[str]] = {}
    for industry, group in frame.groupby("industry"):
        tickers = [str(value).strip().upper() for value in group["ticker"].dropna() if str(value).strip()]
        result[str(industry).strip().casefold()] = tickers
    return result


def resolve_peer_tickers(
    company_industry: str,
    manual_text: str,
    peer_groups: dict[str, list[str]],
) -> list[str]:
    """Combine manual tickers with an exact industry match from the peer-group file."""
    manual = [part.strip().upper() for part in manual_text.replace("\n", ",").split(",") if part.strip()]
    file_peers = peer_groups.get(company_industry.strip().casefold(), [])
    seen: set[str] = set()
    combined: list[str] = []
    for ticker in manual + file_peers:
        if ticker not in seen:
            seen.add(ticker)
            combined.append(ticker)
    return combined
