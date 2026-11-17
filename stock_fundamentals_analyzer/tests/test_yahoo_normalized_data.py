import unittest

from calculations.ratios import calculate_company_metrics


class YahooNormalisedDataTests(unittest.TestCase):
    def setUp(self):
        self.company = {
            "General": {"Name": "Example Corp", "CurrencyCode": "USD"},
            "Highlights": {
                "MarketCapitalization": 1_000.0,
                "PERatio": 12.0,
                "PEGRatio": 1.4,
                "ReturnOnEquityTTM": 0.22,
                "DebtToEquity": 0.2,
                "CurrentRatio": 1.7,
            },
            "Valuation": {
                "EnterpriseValue": 1_100.0,
                "TrailingPE": 12.0,
                "PriceSalesTTM": 2.0,
                "EnterpriseValueEbitda": 6.0,
            },
            "Financials": {
                "Income_Statement": {
                    "ttm": [{
                        "date": "2026-09-30", "_is_ttm_aggregate": True,
                        "totalRevenue": 550.0, "netIncome": 110.0, "ebitda": 165.0,
                    }],
                    "yearly": [{
                        "date": "2025-12-31", "totalRevenue": 500.0,
                        "netIncome": 100.0, "ebitda": 150.0,
                    }],
                },
                "Balance_Sheet": {
                    "quarterly": [
                        {"date": "2026-09-30", "totalCurrentAssets": 340.0,
                         "totalCurrentLiabilities": 200.0, "totalStockholderEquity": 550.0,
                         "totalDebt": 110.0, "cash": 60.0},
                        {"date": "2026-06-30", "totalStockholderEquity": 530.0},
                        {"date": "2026-03-31", "totalStockholderEquity": 510.0},
                        {"date": "2025-12-31", "totalStockholderEquity": 480.0},
                        {"date": "2025-09-30", "totalStockholderEquity": 450.0},
                    ],
                    "yearly": [
                        {"date": "2025-12-31", "totalCurrentAssets": 300.0,
                         "totalCurrentLiabilities": 150.0, "totalStockholderEquity": 500.0,
                         "totalDebt": 100.0, "cash": 50.0},
                        {"date": "2024-12-31", "totalStockholderEquity": 400.0},
                    ],
                },
                "Cash_Flow": {
                    "ttm": [{"date": "2026-09-30", "_is_ttm_aggregate": True, "freeCashFlow": 90.0}],
                    "yearly": [{"date": "2025-12-31", "freeCashFlow": 80.0}],
                },
            },
        }

    def test_ttm_uses_yahoo_aggregate_and_converts_quote_statistics(self):
        metrics = calculate_company_metrics(self.company, "TTM")
        self.assertEqual(metrics["pe"], 12.0)
        self.assertEqual(metrics["ps"], 2.0)
        self.assertEqual(metrics["peg"], 1.4)
        self.assertAlmostEqual(metrics["de"], 0.2)
        self.assertAlmostEqual(metrics["roe"], 0.22)
        self.assertAlmostEqual(metrics["p_fcf"], 1_000 / 90)
        self.assertEqual(metrics["ev_ebitda"], 6.0)
        self.assertAlmostEqual(metrics["cr"], 1.7)

    def test_fy_uses_latest_annual_statements_not_current_quote_debt_and_current_ratio(self):
        metrics = calculate_company_metrics(self.company, "FY")
        self.assertAlmostEqual(metrics["pe"], 1_000 / 100)
        self.assertAlmostEqual(metrics["ps"], 1_000 / 500)
        self.assertEqual(metrics["peg"], 1.4)  # current estimate-based PEG, not a historical FY multiple
        self.assertAlmostEqual(metrics["de"], 100 / 500)
        self.assertAlmostEqual(metrics["roe"], 100 / ((500 + 400) / 2))
        self.assertAlmostEqual(metrics["p_fcf"], 1_000 / 80)
        self.assertAlmostEqual(metrics["ev_ebitda"], 1_100 / 150)
        self.assertAlmostEqual(metrics["cr"], 2.0)


if __name__ == "__main__":
    unittest.main()
