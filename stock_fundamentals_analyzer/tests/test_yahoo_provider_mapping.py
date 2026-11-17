import unittest

import pandas as pd

from data.providers.yahoo import YahooFinanceProvider, _frame_records


class YahooProviderMappingTests(unittest.TestCase):
    def test_maps_common_yahoo_income_statement_labels(self):
        frame = pd.DataFrame(
            {
                pd.Timestamp("2025-12-31"): [500.0, 100.0, 150.0],
                pd.Timestamp("2024-12-31"): [450.0, 90.0, 130.0],
            },
            index=["Total Revenue", "Net Income", "EBITDA"],
        )
        records = _frame_records(frame, "income")
        self.assertEqual(records[0]["date"], "2025-12-31")
        self.assertEqual(records[0]["totalRevenue"], 500.0)
        self.assertEqual(records[0]["netIncome"], 100.0)
        self.assertEqual(records[0]["ebitda"], 150.0)

    def test_marks_ttm_aggregate_record(self):
        frame = pd.DataFrame(
            {pd.Timestamp("2026-09-30"): [90.0]},
            index=["Free Cash Flow"],
        )
        records = _frame_records(frame, "cashflow", ttm_aggregate=True)
        self.assertTrue(records[0]["_is_ttm_aggregate"])
        self.assertEqual(records[0]["freeCashFlow"], 90.0)

    def test_industry_company_lookup_supports_symbol_index(self):
        class FakeIndustry:
            def __init__(self, key, region="US"):
                self.top_performing_companies = pd.DataFrame(
                    {"name": ["Example Corp"]}, index=pd.Index(["EXM"], name="symbol")
                )

        class FakeYahoo:
            Industry = FakeIndustry

        provider = YahooFinanceProvider.__new__(YahooFinanceProvider)
        provider.yf = FakeYahoo
        rows = provider.get_industry_companies("software-infrastructure", region="DE", limit=5)
        self.assertEqual(rows[0]["Symbol"], "EXM")
        self.assertEqual(rows[0]["Name"], "Example Corp")


if __name__ == "__main__":
    unittest.main()
