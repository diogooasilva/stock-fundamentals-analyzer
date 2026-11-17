from __future__ import annotations

from statistics import mean, median
from typing import Any

from calculations.ratios import calculate_company_metrics
from config.thresholds import METRIC_ORDER


def build_peer_benchmarks(
    peer_fundamentals: list[dict[str, Any]], period: str
) -> dict[str, dict[str, float | int | None]]:
    """Calculate simple peer-sample mean and median for every available metric."""
    values_by_metric: dict[str, list[float]] = {metric: [] for metric in METRIC_ORDER}
    for peer in peer_fundamentals:
        metrics = calculate_company_metrics(peer, period)
        for metric in METRIC_ORDER:
            value = metrics.get(metric)
            if value is not None:
                values_by_metric[metric].append(float(value))

    return {
        metric: {
            "mean": mean(values) if values else None,
            "median": median(values) if values else None,
            "count": len(values),
        }
        for metric, values in values_by_metric.items()
    }


def compare_to_benchmarks(
    company_metrics: dict[str, float | None],
    benchmarks: dict[str, dict[str, float | int | None]],
) -> dict[str, dict[str, str | None]]:
    results: dict[str, dict[str, str | None]] = {}
    for metric in METRIC_ORDER:
        company_value = company_metrics.get(metric)
        benchmark = benchmarks.get(metric, {}).get("median")
        if company_value is None or benchmark is None or float(benchmark) == 0:
            results[metric] = {"median_difference": None, "median_difference_label": "N/A"}
            continue
        difference = (company_value / float(benchmark) - 1.0) * 100.0
        results[metric] = {
            "median_difference": difference,
            "median_difference_label": f"{difference:+.1f}%",
        }
    return results
