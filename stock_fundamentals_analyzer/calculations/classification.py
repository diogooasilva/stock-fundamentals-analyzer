from __future__ import annotations

from typing import Any

from config.thresholds import METRIC_LABELS, METRIC_ORDER, THRESHOLDS


def assess_one(metric: str, value: float | None, thresholds: dict[str, dict[str, float | str]] | None = None) -> dict[str, str]:
    if value is None:
        return {"status": "Not available", "comment": "The required source data was not available or the ratio was not meaningful."}

    rule = (thresholds or THRESHOLDS)[metric]
    kind = rule["kind"]

    if metric == "peg" and value <= 0:
        return {"status": "Not meaningful", "comment": "PEG is not useful when the growth input is zero or negative."}

    if kind == "upper":
        if value > 0 and value < rule["max"]:
            return {"status": "Favourable", "comment": f"Below the preferred threshold of {rule['max']:g}."}
        return {"status": "Outside target", "comment": f"At or above the preferred threshold of {rule['max']:g}."}

    minimum, maximum = rule["min"], rule["max"]
    if minimum <= value <= maximum:
        return {"status": "Favourable", "comment": f"Within the preferred range of {minimum:g}–{maximum:g}."}
    if value > maximum:
        if metric == "roe":
            return {"status": "Above target", "comment": "Above the target range; strong ROE can be positive, but check leverage and earnings quality."}
        if metric == "cr":
            return {"status": "Above target", "comment": "Above the target range; unusually high liquidity may indicate underused assets."}
        return {"status": "Outside target", "comment": f"Above the preferred range of {minimum:g}–{maximum:g}."}
    if metric == "cr":
        return {"status": "Outside target", "comment": "Below 1 can indicate that current liabilities exceed current assets."}
    return {"status": "Outside target", "comment": f"Below the preferred range of {minimum:g}–{maximum:g}."}


def assess_metrics(metrics: dict[str, float | None], thresholds: dict[str, dict[str, float | str]] | None = None) -> dict[str, dict[str, str]]:
    return {metric: assess_one(metric, metrics.get(metric), thresholds) for metric in METRIC_ORDER}


def calculate_score(assessments: dict[str, dict[str, str]]) -> dict[str, Any]:
    evaluated = [
        item for item in assessments.values()
        if item.get("status") not in {"Not available", "Not meaningful"}
    ]
    favourable = sum(1 for item in evaluated if item.get("status") == "Favourable")
    score = favourable / len(evaluated) * 100 if evaluated else None
    return {"score": score, "favourable": favourable, "evaluated": len(evaluated)}
