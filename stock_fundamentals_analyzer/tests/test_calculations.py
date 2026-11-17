import unittest

from calculations.classification import assess_metrics, calculate_score
from calculations.industry import build_peer_benchmarks, compare_to_benchmarks
from calculations.ratios import calculate_company_metrics, format_metric_value


def fake_fundamentals(
    ticker: str,
    market_cap: float,
    revenue: float,
    net_income: float,
    ebitda: float,
    fcf: float,
    equity: float,
    debt: float,
    current_assets: float,
    current_liabilities: float,
    eps_values: list[float],
) -> dict:
    yearly_income = {}
    yearly_cash = {}
    yearly_balance = {}
    for i, year in enumerate(("2025", "2024", "2023")):
        yearly_income[f"{year}-12-31"] = {
            "date": f"{year}-12-31",
            "totalRevenue": str(revenue * (0.85 + i * 0.05)),
            "netIncome": str(net_income * (0.85 + i * 0.05)),
            "ebitda": str(ebitda * (0.85 + i * 0.05)),
        }
        yearly_cash[f"{year}-12-31"] = {"date": f"{year}-12-31", "freeCashFlow": str(fcf * (0.85 + i * 0.05))}
        yearly_balance[f"{year}-12-31"] = {
            "date": f"{year}-12-31",
            "totalStockholderEquity": str(equity * (0.9 + i * 0.05)),
            "totalDebt": str(debt),
            "totalCurrentAssets": str(current_assets),
            "totalCurrentLiabilities": str(current_liabilities),
        }

    quarterly_income = {}
    quarterly_cash = {}
    quarterly_balance = {}
    for i in range(5):
        quarter = f"2026-0{4-i}-31"
        quarterly_income[quarter] = {
            "date": quarter,
            "totalRevenue": str(revenue / 4),
            "netIncome": str(net_income / 4),
            "ebitda": str(ebitda / 4),
        }
        quarterly_cash[quarter] = {"date": quarter, "freeCashFlow": str(fcf / 4)}
        quarterly_balance[quarter] = {
            "date": quarter,
            "totalStockholderEquity": str(equity),
            "totalDebt": str(debt),
            "totalCurrentAssets": str(current_assets),
            "totalCurrentLiabilities": str(current_liabilities),
        }

    return {
        "General": {"Code": ticker, "Name": ticker, "Industry": "Test Industry", "CurrencyCode": "USD"},
        "Highlights": {"MarketCapitalization": market_cap, "RevenueTTM": revenue, "PEGRatio": 0.8, "ReturnOnEquityTTM": net_income / equity},
        "Valuation": {"TrailingPE": market_cap / net_income, "PriceSalesTTM": market_cap / revenue, "EnterpriseValue": market_cap + debt},
        "Earnings": {"Annual": {
            f"{year}-12-31": {"date": f"{year}-12-31", "epsActual": eps}
            for year, eps in zip(("2023", "2024", "2025"), eps_values)
        }},
        "Financials": {
            "Income_Statement": {"yearly": yearly_income, "quarterly": quarterly_income},
            "Cash_Flow": {"yearly": yearly_cash, "quarterly": quarterly_cash},
            "Balance_Sheet": {"yearly": yearly_balance, "quarterly": quarterly_balance},
        },
    }


class CalculationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.company = fake_fundamentals(
            "AAA", 2_000, 1_000, 100, 200, 150, 500, 200, 300, 200, [1.0, 1.2, 1.5]
        )

    def test_ttm_metrics(self) -> None:
        metrics = calculate_company_metrics(self.company, "TTM")
        self.assertAlmostEqual(metrics["pe"], 20.0)
        self.assertAlmostEqual(metrics["ps"], 2.0)
        self.assertAlmostEqual(metrics["de"], 0.4)
        self.assertAlmostEqual(metrics["p_fcf"], 2000 / 150)
        self.assertAlmostEqual(metrics["cr"], 1.5)

    def test_fy_metrics(self) -> None:
        metrics = calculate_company_metrics(self.company, "FY")
        self.assertAlmostEqual(metrics["pe"], 2_000 / 85)
        self.assertAlmostEqual(metrics["ps"], 2_000 / 850)
        self.assertAlmostEqual(metrics["de"], 200 / 450)
        self.assertIsNotNone(metrics["peg"])
        self.assertAlmostEqual(metrics["cr"], 1.5)

    def test_classification_and_score(self) -> None:
        metrics = {"pe": 18.0, "ps": 1.5, "peg": 0.8, "de": 0.5, "roe": 0.17, "p_fcf": 8.0, "ev_ebitda": 9.0, "cr": 1.5}
        assessments = assess_metrics(metrics)
        self.assertTrue(all(item["status"] == "Favourable" for item in assessments.values()))
        score = calculate_score(assessments)
        self.assertEqual(score["score"], 100.0)

    def test_peer_benchmarks_and_comparison(self) -> None:
        peer_a = fake_fundamentals("BBB", 1_800, 1_000, 120, 210, 180, 600, 180, 320, 200, [1.0, 1.1, 1.2])
        peer_b = fake_fundamentals("CCC", 2_200, 1_000, 80, 190, 120, 450, 250, 280, 200, [1.0, 1.1, 1.2])
        benchmarks = build_peer_benchmarks([peer_a, peer_b], "TTM")
        self.assertEqual(benchmarks["pe"]["count"], 2)
        company_metrics = calculate_company_metrics(self.company, "TTM")
        comparison = compare_to_benchmarks(company_metrics, benchmarks)
        self.assertIsNotNone(comparison["pe"]["median_difference"])

    def test_format_percent(self) -> None:
        self.assertEqual(format_metric_value("roe", 0.175), "17.5%")


if __name__ == "__main__":
    unittest.main()
