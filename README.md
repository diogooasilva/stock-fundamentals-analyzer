# stock-fundamentals-analyzer
Interactive stock fundamental analysis and comparison dashboard powered by Yahoo Finance
# Equity Insights — Stock Fundamentals Analyzer

A Streamlit-based personal equity research workspace using Yahoo Finance through `yfinance`. It combines a hybrid dark-navigation/light-workspace interface with fundamental ratio analysis, graphical share-price performance, automatic Yahoo industry peer samples, comparisons, watchlists and exports.

## What's included

- Hybrid UI: dark navy navigation rail and clean light research workspace.
- Stock Analysis is the first page. Company search returns Yahoo Finance suggestions while the user types (from two characters).
- A single dark quote banner containing last price and daily deviation, market capitalisation, 52-week high/low and sector.
- Eight fundamental indicators: P/E, Price/Sales, PEG, Debt/Equity, ROE, Price/Free Cash Flow, EV/EBITDA and Current Ratio.
- TTM and latest completed FY views, using the existing calculation and classification modules. Each metric has an expandable definition and a colour-coded assessment.
- Editable screening thresholds, held in Streamlit session state.
- Multi-company comparison for up to 20 companies. The Compare button on Stock Analysis adds the current ticker to the Compare Stocks session list; the Compare Stocks overview is populated automatically from that list.
- Automatic Yahoo Finance industry top-company sample, with peer-sample mean, median, sample count and deviation from peer median. The app identifies this as a returned sample, not a complete industry census.
- Graphical stock performance directly on Stock Analysis, with 1M, 3M, 6M, 1Y and 5Y range buttons. The separate Financial History and Industry Analysis pages have been removed.
- Session-only watchlist.
- Excel and PDF exports for analysis; Excel exports for comparisons and peer analysis.
- Six-hour cache for company fundamentals/search and one-hour cache for price history.

## Storage behaviour

The selected storage mode is **session only**. Watchlists, companies selected for comparison, comparison results and threshold changes are held in Streamlit session state. They are not written to a database or local file. They reset when the Streamlit session ends or is cleared. Streamlit's in-memory data cache may temporarily retain provider responses according to the cache TTLs above.

## Data provider and licensing

The application uses Yahoo Finance data through `yfinance`; no API key is required. `yfinance` is an open-source interface to Yahoo Finance endpoints, not an official Yahoo Finance commercial API. Its documentation describes personal/research/educational use. Review Yahoo's current terms and obtain permission before commercial use, redistribution or public-facing deployment. Data availability, field names, quote freshness, rate limits and statement history vary by company and exchange.

For Stock Analysis, the app asks Yahoo Finance for the industry company list associated with the company's Yahoo industry key (using Yahoo's top-company field where available, or its top-performing/top-growth company lists in the installed yfinance version) and loads the returned tickers to calculate TTM/FY peer statistics. This is an automatically retrieved Yahoo sample, not a Yahoo-published industry-wide mean/median or a complete census of every listed company. If Yahoo does not return an industry key or peer list, the benchmark is shown as unavailable rather than fabricated.

## Windows installation (PowerShell)

Use Python 3.12 (64-bit) or another compatible Python version.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt
```

If PowerShell blocks environment activation:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

## Run

```powershell
streamlit run app.py
```

Streamlit normally opens at `http://localhost:8501`.

## Tests

```powershell
python -m unittest discover -s tests -v
```

The unit tests use synthetic data and validate the calculation layer, Yahoo statement mapping and normalisation. They do not make live Yahoo requests and do not guarantee that Yahoo will return every field for every ticker.

## Project structure

```text
stock_fundamentals_analyzer/
├── app.py
├── calculations/
│   ├── classification.py
│   ├── industry.py
│   └── ratios.py
├── config/
│   ├── thresholds.py
│   └── peer_groups.csv
├── data/
│   ├── peer_groups.py
│   └── providers/yahoo.py
├── tests/
├── requirements.txt
└── README.md
```

## Ratio methodology and caveats

- Yahoo-published quote statistics are used when available; selected metrics are calculated from statements as fallbacks.
- Debt/Equity is normalised from Yahoo's percentage-style quote field to a ratio multiple.
- P/FCF is calculated from market capitalisation and FCF. Non-positive FCF is not treated as a meaningful positive valuation multiple.
- ROE uses Yahoo's quote value when available for TTM and statement-based calculations otherwise.
- PEG is a current estimate-based quote statistic, not a historical FY PEG. It may appear in both TTM and FY views with this caveat.
- FY valuation multiples use current market capitalisation/enterprise value divided by the latest completed FY financial measure. They are not historical fiscal-year-end valuation multiples.
- Balance-sheet ratios are point-in-time measures, not TTM flows.
- Financial-sector companies may require different ratio definitions and should not be compared mechanically with non-financial companies.

The default fundamental thresholds are in `config/thresholds.py`; session changes are made in the Screening Settings page and do not edit that file. The standalone Stock Screener, Industry Analysis and Financial History pages have been removed; multi-company evaluation is handled in Compare Stocks and price history is shown on Stock Analysis.

## Disclaimer

This application is an educational screening and research tool, not investment advice. Financial data can be delayed, incomplete, inconsistent or revised. Do not use it as the sole basis for an investment decision.

## Latest UI refinements

- Consistent navy industry-companies and summary banners, plus breathing space before ratios.
- Inline, color-coded metric assessments within metric accordion headers.
- Expand all / Collapse all toggles for both Stock Analysis and Compare Stocks; individual sections still toggle separately.
- Zero-anchored non-negative ruler scales and support for negative company/peer values on both pages.
- Company tickers in the metric legends, and removable one-piece ticker pills in comparisons and watchlists.
- Currency symbols on prices and abbreviated K/M/B/T market caps on the watchlist. Values remain in the original listing currency.

Note: Company removal pills are single clickable buttons: clicking the ticker or its × removes that entry.
