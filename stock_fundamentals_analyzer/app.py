from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from calculations.classification import assess_metrics, calculate_score
from calculations.industry import build_peer_benchmarks, compare_to_benchmarks
from calculations.ratios import calculate_company_metrics, format_metric_value
from config.thresholds import METRIC_LABELS, METRIC_ORDER, THRESHOLDS
from data.providers.yahoo import YahooFinanceProvider, ProviderError

ROOT = Path(__file__).resolve().parent

st.set_page_config(page_title="Equity Insights | Stock Fundamentals Analyzer", page_icon="◈", layout="wide", initial_sidebar_state="expanded")

# Hybrid design: dark navigation rail + bright research workspace.
st.markdown("""
<style>
:root { --ink:#14243a; --muted:#718096; --line:#e6ebf2; --navy:#101d31; --teal:#12a887; }
.block-container {padding-top:1.35rem; padding-bottom:2.5rem; max-width:1500px;}
[data-testid="stSidebar"] {background:linear-gradient(180deg,#101d31 0%,#172941 100%);}
[data-testid="stSidebar"] * {color:#edf4fb !important;}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {color:#b8c6d8 !important;}
[data-testid="stSidebar"] [data-baseweb="select"] * {color:#14243a !important;}
[data-testid="stSidebar"] [data-testid="stRadio"] label {padding: .35rem .15rem;}
[data-testid="stMetric"] {background:#fff;border:1px solid #e7edf4;padding:14px 16px;border-radius:13px;box-shadow:0 2px 10px rgba(18,36,58,.035);}
[data-testid="stMetricLabel"] p {color:#718096 !important;font-size:.78rem;}
[data-testid="stMetricValue"] {color:#14243a;font-weight:700;}
[data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"] {gap: .85rem;}
.eyebrow {color:#12a887;text-transform:uppercase;letter-spacing:.13em;font-size:.70rem;font-weight:800;}
.hero {background:linear-gradient(115deg,#12233a 0%,#203d59 70%,#126e70 130%);padding:1.15rem 1.5rem;border-radius:18px;color:#fff;margin-bottom:1rem;display:flex;align-items:center;justify-content:space-between;gap:1rem;}
.hero-price {text-align:right;min-width:170px;} .hero-price-label {color:#b8c9d9;text-transform:uppercase;letter-spacing:.08em;font-size:.7rem;font-weight:700;} .hero-price-value {color:#fff;font-size:clamp(1.25rem,2.1vw,2rem);font-weight:800;white-space:nowrap;} .hero-price-change {font-size:.82rem;font-weight:700;}
.dark-stat-row {display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:.75rem;margin:.7rem 0 1rem;} .dark-stat {background:linear-gradient(110deg,#101d31,#20334d);border:1px solid #314760;border-radius:13px;padding:13px 16px;min-width:0;} .dark-stat-label {color:#aebed0;font-size:.7rem;text-transform:uppercase;letter-spacing:.06em;font-weight:700;} .dark-stat-value {color:#fff;font-size:1.25rem;font-weight:800;margin-top:.2rem;}
.assessment-pill {display:inline-block;padding:5px 10px;border-radius:999px;font-size:.76rem;font-weight:800;white-space:nowrap;}
.metric-row {border:1px solid #e4eaf1;border-radius:12px;padding:10px 12px;margin:5px 0;background:#fff;} .metric-head {font-size:.68rem;color:#718096;text-transform:uppercase;font-weight:750;letter-spacing:.04em;}
.metric-scale-wrap{padding:16px 8px 8px;margin:7px 0 8px;background:#101d31;border:1px solid #344b65;border-radius:12px}.metric-scale{height:12px;background:#34465c;border:1px solid #60758e;border-radius:99px;position:relative;margin:25px 16px 24px}.metric-target{position:absolute;top:-2px;height:14px;background:linear-gradient(90deg,#f3c969,#65e0b5);border:1px solid #fff0b5;border-radius:99px;box-shadow:0 0 12px rgba(101,224,181,.5)}.metric-dot{position:absolute;top:50%;width:15px;height:15px;border:2px solid #fff;border-radius:50%;transform:translate(-50%,-50%);box-shadow:0 0 0 2px #101d31,0 0 10px rgba(255,255,255,.35);z-index:3}.metric-dot-label{position:absolute;top:-27px;transform:translateX(-50%);font-size:11px;font-weight:850;white-space:nowrap;color:#fff;text-shadow:0 1px 3px #000;z-index:4}.metric-target-label{position:absolute;top:15px;transform:translateX(-50%);font-size:11px;font-weight:850;white-space:nowrap;color:#ffe39a;text-shadow:0 1px 3px #000}.metric-legend{display:flex;gap:14px;flex-wrap:wrap;margin-top:4px;padding:5px 7px 0}.metric-legend-item{font-size:12px;color:#f0f5fb;font-weight:750;display:flex;align-items:center;gap:6px}.metric-legend-dot{width:10px;height:10px;border-radius:50%;display:inline-block;border:1px solid #fff}.company-chip{display:inline-flex;align-items:center;gap:5px;background:#172a40;border:1px solid #405873;border-radius:999px;padding:5px 7px 5px 11px;margin:3px 0;font-size:.82rem;color:#f3f7fc}.company-chip strong{font-weight:750}.metric-expander-label{color:#f5f8fc;font-weight:800}
div[data-testid="stPopover"] > button {width:100%;min-height:62px;background:linear-gradient(110deg,#101d31,#20334d)!important;color:#fff!important;border:1px solid #405873!important;border-radius:13px!important;font-weight:800!important;white-space:normal!important;}
div[data-testid="stPopover"] > button:hover {border-color:#65e0b5!important;color:#fff!important;}
/* Compact, aligned summary cards. The industry popover is styled as the third card. */
.dark-stat {
  background:linear-gradient(110deg,#101d31,#20334d);
  border:1px solid #314760;
  border-radius:13px;
  box-sizing:border-box;
  min-height:84px;
  padding:11px 14px;
  margin-right:7px;
}
.dark-stat-label {font-size:.68rem;line-height:1.3;}
.dark-stat-value {font-size:1.20rem;line-height:1.35;margin-top:.28rem;}
/* Selector does not assume that Streamlit places the button directly under stPopover. */
[class*="st-key-industry_company_banner_"] {margin-right:7px;}
[class*="st-key-industry_company_banner_"] button {
  background:linear-gradient(110deg,#101d31,#20334d)!important;
  border:1px solid #314760!important;
  border-radius:13px!important;
  box-sizing:border-box!important;
  min-height:84px!important;
  height:84px!important;
  width:100%!important;
  padding:11px 14px!important;
  display:flex!important;
  justify-content:space-between!important;
  align-items:center!important;
  text-align:left!important;
  color:#fff!important;
}
[class*="st-key-industry_company_banner_"] button:hover {border-color:#65e0b5!important;}
[class*="st-key-industry_company_banner_"] button p {
  color:#aebed0!important;
  text-align:left!important;
  font-size:.68rem!important;
  font-weight:700!important;
  letter-spacing:.06em!important;
  line-height:1.55!important;
  margin:0!important;
}
[class*="st-key-industry_company_banner_"] button strong {
  display:inline-block!important;
  color:#fff!important;
  font-size:1.20rem!important;
  font-weight:800!important;
  letter-spacing:normal!important;
  margin-top:4px!important;
}
/* The assessment is an actual right-edge element of the accordion summary,
   rather than a Markdown span nested in the title paragraph. */
[class*="st-key-assessment_"] [data-testid="stExpander"] summary {
  display:flex!important;
  align-items:center!important;
  width:100%!important;
}
[class*="st-key-assessment_"] [data-testid="stExpander"] summary::after {
  content:"Assessment";
  display:inline-flex!important;
  align-items:center!important;
  flex:0 0 auto!important;
  margin-left:auto!important;
  margin-right:8px!important;
  padding:5px 11px!important;
  border-radius:8px!important;
  border:1px solid #94a3b8!important;
  background:#4a5568!important;
  color:#fff!important;
  font-size:.85rem!important;
  line-height:1.3!important;
  font-weight:800!important;
  white-space:nowrap!important;
}
[class*="st-key-assessment_"][class*="_favourable"] [data-testid="stExpander"] summary::after {content:"Favourable";background:#086b4d!important;color:#e2fff2!important;border-color:#33e0a4!important;box-shadow:0 0 0 1px #33e0a433!important;}
[class*="st-key-assessment_"][class*="_outside_target"] [data-testid="stExpander"] summary::after {content:"Outside target";background:#874000!important;color:#fff2dc!important;border-color:#ffb44d!important;box-shadow:0 0 0 1px #ffb44d33!important;}
[class*="st-key-assessment_"][class*="_above_target"] [data-testid="stExpander"] summary::after {content:"Above target";background:#174b9a!important;color:#e6f3ff!important;border-color:#78baff!important;}
[class*="st-key-assessment_"][class*="_not_meaningful"] [data-testid="stExpander"] summary::after {content:"Not meaningful";background:#64368a!important;color:#fff0ff!important;border-color:#cb9bfa!important;}
[class*="st-key-assessment_"][class*="_not_available"] [data-testid="stExpander"] summary::after {content:"Not available";}
/* Action buttons are compact, left aligned and distinct from the accordion background. */
[class*="st-key-analysis_"][class*="_expand_collapse"] button,
.st-key-compare_expand_collapse button {
 background:#17647b!important;color:#fff!important;border:1px solid #3ab6c5!important;
 border-radius:10px!important;min-height:38px!important;font-weight:750!important;
}
[class*="st-key-analysis_"][class*="_expand_collapse"] button:hover,
.st-key-compare_expand_collapse button:hover {background:#23849b!important;border-color:#7de1dc!important;}

/* Each removal action is a clickable ticker pill without an × symbol. */
.st-key-remove_compare, .st-key-remove_watch {min-width:0;}
div[class*="st-key-remove_compare_"] button, div[class*="st-key-remove_watch_"] button {border-radius:999px!important;background:#172a40!important;border:1px solid #405873!important;color:#f3f7fc!important;font-weight:750!important;min-height:36px;padding:.25rem .7rem!important;}
div[class*="st-key-remove_compare_"] button:hover, div[class*="st-key-remove_watch_"] button:hover {border-color:#65e0b5!important;background:#203b57!important;}
/* A little breathing space between the summary banners and the ratio accordions. */
.metric-section-gap {height:18px;}

.compare-hint {color:#b9c9d8;font-size:.72rem;}
.market-banner {display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:0;background:linear-gradient(110deg,#101d31,#20334d);border:1px solid #314760;border-radius:14px;overflow:hidden;margin:.8rem 0 1.2rem;}
.market-cell {padding:13px 15px;min-width:0;border-right:1px solid #40516a;}
.market-cell:last-child {border-right:0;}
.market-label {color:#aebed0;font-size:clamp(.62rem,.75vw,.78rem);font-weight:650;letter-spacing:.035em;text-transform:uppercase;white-space:nowrap;}
.market-value {color:#fff;font-size:clamp(.78rem,1.2vw,1.12rem);font-weight:750;line-height:1.35;overflow-wrap:anywhere;}
.market-change {color:#8ce0c5;font-size:clamp(.65rem,.85vw,.82rem);font-weight:650;}
.performance-banner {display:grid;grid-template-columns:repeat(4,minmax(0,1fr));background:linear-gradient(110deg,#101d31,#20334d);border:1px solid #314760;border-radius:14px;overflow:hidden;margin:.55rem 0 1.1rem;}
.performance-cell {padding:11px 15px;border-right:1px solid #40516a;min-width:0;}
.performance-cell:last-child {border-right:0;}
.performance-value {color:#fff;font-size:clamp(.82rem,1.15vw,1.08rem);font-weight:750;}
.performance-label {color:#aebed0;font-size:clamp(.62rem,.75vw,.78rem);text-transform:uppercase;letter-spacing:.04em;}
@media(max-width:900px){.market-banner{grid-template-columns:repeat(3,minmax(0,1fr));}.market-cell:nth-child(3){border-right:0;}.market-cell:nth-child(n+4){border-top:1px solid #40516a;}}
@media(max-width:560px){.market-banner{grid-template-columns:repeat(2,minmax(0,1fr));}.market-cell:nth-child(odd){border-right:1px solid #40516a;}.market-cell:nth-child(even){border-right:0;}.market-cell:nth-child(n+3){border-top:1px solid #40516a;}}
.hero h1 {color:#fff !important;margin:.15rem 0 .2rem 0;font-size:1.8rem;}
.hero p {color:#d3dfeb;margin:0;}
.section-title {font-size:1.08rem;font-weight:750;color:#14243a;margin:.35rem 0 .65rem 0;}
.small-note {font-size:.78rem;color:#718096;}
div[data-testid="stDataFrame"] {border:1px solid #e7edf4;border-radius:12px;overflow:hidden;}
.stButton>button[kind="primary"], .stDownloadButton>button {border-radius:9px;}
</style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=6 * 60 * 60, show_spinner=False)
def cached_search(query: str) -> list[dict[str, Any]]:
    return YahooFinanceProvider().search_companies(query, limit=20)


@st.cache_data(ttl=6 * 60 * 60, show_spinner=False)
def cached_fundamentals(ticker: str) -> dict[str, Any]:
    return YahooFinanceProvider().get_fundamentals(ticker)


@st.cache_data(ttl=6 * 60 * 60, show_spinner=False)
def cached_industry_companies(industry_key: str, region: str = "US") -> list[dict[str, Any]]:
    return YahooFinanceProvider().get_industry_companies(industry_key, region=region, limit=25)


@st.cache_data(ttl=60 * 60, show_spinner=False)
def cached_history(ticker: str, period: str = "1y", interval: str = "1d") -> pd.DataFrame:
    rows = YahooFinanceProvider().get_price_history(ticker, period, interval)
    return pd.DataFrame(rows)


def init_state() -> None:
    defaults = {
        "watchlist": [], "compare_selected": [], "search_results": [], "analysis_ticker": "", "analysis_label": "",
        "company_query": "", "last_search_query": "", "fundamentals_session": {}, "compare_tickers": "",
        "thresholds_session": {k: dict(v) for k, v in THRESHOLDS.items()},
        "peer_text_session": "", "active_page": "Stock Analysis", "last_analysis": {},
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def get_fundamentals(ticker: str) -> dict[str, Any]:
    if ticker not in st.session_state["fundamentals_session"]:
        st.session_state["fundamentals_session"][ticker] = cached_fundamentals(ticker)
    return st.session_state["fundamentals_session"][ticker]


def fmt_money(value: Any, currency: str = "") -> str:
    try:
        n = float(value)
        if abs(n) >= 1e12: text = f"{n/1e12:,.2f}T"
        elif abs(n) >= 1e9: text = f"{n/1e9:,.2f}B"
        elif abs(n) >= 1e6: text = f"{n/1e6:,.2f}M"
        elif abs(n) >= 1e3: text = f"{n/1e3:,.2f}K"
        else: text = f"{n:,.2f}"
        return f"{currency}{text}" if currency in {"$", "€", "£", "¥", "₹", "₩"} else f"{currency} {text}".strip()
    except (TypeError, ValueError):
        return "N/A"


def fmt_price(value: Any, currency: str = "") -> str:
    """Unabbreviated price including the listing's original trading currency."""
    try:
        amount = f"{float(value):,.2f}"
        return f"{currency}{amount}" if currency in {"$", "€", "£", "¥", "₹", "₩"} or currency.endswith("$") else f"{currency} {amount}".strip()
    except (ValueError, TypeError):
        return "N/A"

def company_metrics(fundamentals: dict[str, Any], period: str) -> dict[str, float | None]:
    return calculate_company_metrics(fundamentals, period)


def profile(f: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    return f.get("General", {}), f.get("Highlights", {})


def score_label(value: float | None) -> str:
    return f"{value:.0f}/100" if value is not None else "N/A"


METRIC_EXPLANATIONS = {
    "pe": "Price-to-Earnings compares the share price with earnings per share. Lower values can indicate a cheaper valuation, but compare companies with similar growth, risk and accounting profiles. Negative or unavailable earnings make this multiple unsuitable.",
    "ps": "Price-to-Sales compares the company's market value with its revenue. It is useful when earnings are low or volatile, but margins matter: a high-margin business can justify a higher multiple.",
    "peg": "The PEG ratio divides the P/E ratio by expected earnings growth. It attempts to account for growth, but depends heavily on forecast quality and is not meaningful with zero or negative growth.",
    "de": "Debt-to-Equity compares interest-bearing debt with shareholders' equity. It indicates financial leverage. Capital-intensive businesses and financial institutions can naturally have very different levels.",
    "roe": "Return on Equity measures net income relative to shareholders' equity. Higher ROE can signal efficient use of capital, but unusually high ROE may also result from high debt or very low equity.",
    "p_fcf": "Price-to-Free-Cash-Flow compares market value with cash generated after capital expenditure. It focuses on cash generation, but becomes meaningless when free cash flow is negative.",
    "ev_ebitda": "Enterprise Value-to-EBITDA compares the value of the whole business (equity plus net debt) with operating earnings before interest, taxes, depreciation and amortisation. It helps compare capital structures, but ignores capital expenditure and working capital.",
    "cr": "The Current Ratio compares current assets with current liabilities. It is a short-term liquidity indicator. A value below 1 may signal liquidity pressure; an excessively high value can mean assets are not being used efficiently.",
}


def metric_table(metrics: dict[str, float | None], thresholds: dict[str, Any], peers: list[dict[str, Any]] | None = None, period: str = "TTM") -> tuple[pd.DataFrame, dict[str, Any]]:
    assessments = assess_metrics(metrics, thresholds)
    benchmarks = build_peer_benchmarks(peers or [], period)
    comparisons = compare_to_benchmarks(metrics, benchmarks)
    rows = []
    for key in METRIC_ORDER:
        b = benchmarks.get(key, {})
        rows.append({
            "Metric": METRIC_LABELS[key], "Company": format_metric_value(key, metrics.get(key)),
            "Industry median": format_metric_value(key, b.get("median")),
            "Industry mean": format_metric_value(key, b.get("mean")), "Companies": b.get("count", 0),
            "vs median": comparisons.get(key, {}).get("median_difference_label", "N/A"),
            "Assessment": assessments[key]["status"],
        })
    return pd.DataFrame(rows), {"assessments": assessments, "benchmarks": benchmarks, "comparison": comparisons, "score": calculate_score(assessments)}


def style_assessment_table(frame: pd.DataFrame):
    palette = {
        "Favourable": "background-color:#d9f3e8;color:#116149;font-weight:700",
        "Above target": "background-color:#dcecff;color:#174f83;font-weight:700",
        "Outside target": "background-color:#fff0d6;color:#80520b;font-weight:700",
        "Not meaningful": "background-color:#eee8fb;color:#5b4387;font-weight:700",
        "Not available": "background-color:#edf0f4;color:#596579;font-weight:700",
    }
    return frame.style.map(lambda value: palette.get(str(value), ""), subset=["Assessment"])

def metric_scale_html(key: str, threshold: dict[str, Any], points: list[tuple], height: int = 0) -> str:
    """Render a dark, high-contrast target ruler with hoverable value markers."""
    from html import escape
    valid = []
    for point in points:
        label, value, color = point[:3]
        legend_label = point[3] if len(point) > 3 else label
        if value is not None and pd.notna(value):
            valid.append((str(label), float(value), str(color), str(legend_label)))
    tmin = float(threshold.get("min", 0)) if threshold.get("kind") == "range" else 0.0
    tmax = float(threshold.get("max", 1))
    data_min = min([v for _, v, _, _ in valid] + [tmin, 0.0])
    data_max = max([v for _, v, _, _ in valid] + [tmax])
    span = max(data_max - data_min, abs(data_max) * .05, 1e-9)
    # Keep zero anchored at the beginning for non-negative data; extend left
    # only when a company or peer has a negative value.
    axis_min = data_min - span * .08 if data_min < 0 else 0.0
    axis_max = data_max + span * .12
    axis_span = max(axis_max - axis_min, 1e-9)
    pos = lambda value: max(0.0, min(100.0, (value - axis_min) / axis_span * 100))
    target_left, target_right = pos(tmin), pos(tmax)
    markers = []
    legend = []
    for label, value, color, legend_label in valid:
        x = pos(value)
        shown = format_metric_value(key, value)
        markers.append(
            f"<span class='metric-dot' style='left:{x:.2f}%;background:{escape(color)}' title='{escape(label)}: {escape(str(shown))}'></span>"
            f"<span class='metric-dot-label' style='left:{x:.2f}%'>{escape(label)}</span>"
        )
        legend.append(f"<span class='metric-legend-item'><i class='metric-legend-dot' style='background:{escape(color)}'></i>{escape(legend_label)} · {escape(str(shown))}</span>")
    left_label = format_metric_value(key, tmin) if threshold.get("kind") == "range" else "0"
    right_label = format_metric_value(key, tmax)
    # Edge labels stay inside the bar when the good range begins at zero.
    start_style = "transform:translateX(0)" if target_left < 1 else ""
    end_style = "transform:translateX(-100%)" if target_right > 99 else ""
    target_labels = (f"<span class='metric-target-label' style='left:{target_left:.2f}%;{start_style}'>{escape(str(left_label))}</span>"
                     f"<span class='metric-target-label' style='left:{target_right:.2f}%;{end_style}'>{escape(str(right_label))}</span>")
    return (f"<div class='metric-scale-wrap'><div class='metric-scale'><span class='metric-target' style='left:{target_left:.2f}%;width:{max(0,target_right-target_left):.2f}%'></span>{''.join(markers)}{target_labels}</div>"
            f"<div class='metric-legend'>{''.join(legend)}</div></div>")


def remove_chip_row(label: str, tickers: list[str], state_key: str, prefix: str) -> None:
    """Compact ticker pills; clicking anywhere on a pill removes the ticker."""
    st.caption(label)
    unique = list(dict.fromkeys(tickers))
    per_row = 6
    for offset in range(0, len(unique), per_row):
        batch = unique[offset:offset + per_row]
        cols = st.columns(per_row)
        for col, ticker in zip(cols, batch):
            with col:
                if st.button(ticker, key=f"{prefix}_{ticker}", help=f"Remove {ticker} from this list"):
                    st.session_state[state_key] = [x for x in st.session_state[state_key] if x != ticker]
                    if state_key == "compare_selected":
                        st.session_state["compare_tickers"] = ", ".join(st.session_state[state_key])
                    st.rerun()


def accordion_controls(scope: str) -> bool:
    """A toggle governing the initial expanded state of all metric accordions."""
    key = f"{scope}_metrics_expanded"
    if key not in st.session_state:
        st.session_state[key] = False if scope.startswith("analysis") else True
    expanded = bool(st.session_state[key])
    left, right = st.columns([1.2, 8])
    with left:
        if st.button("Collapse all" if expanded else "Expand all", key=f"{scope}_expand_collapse", width="stretch"):
            st.session_state[key] = not expanded
            st.rerun()
    return expanded


def load_many(tickers: list[str], progress: bool = False) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    unique = list(dict.fromkeys(t.strip().upper() for t in tickers if t.strip()))[:20]
    bar = st.progress(0, text="Loading company data…") if progress and unique else None
    for i, ticker in enumerate(unique, start=1):
        try:
            items.append(get_fundamentals(ticker))
        except ProviderError as exc:
            st.warning(f"{ticker}: {exc}")
        if bar:
            bar.progress(i / len(unique), text=f"Loaded {i} of {len(unique)}")
    if bar:
        bar.empty()
    return items


def currency_symbol(currency: str) -> str:
    symbols = {"USD": "$", "EUR": "€", "GBP": "£", "JPY": "¥", "CNY": "¥", "HKD": "HK$", "CHF": "CHF", "CAD": "C$", "AUD": "A$", "INR": "₹", "KRW": "₩", "SEK": "kr", "NOK": "kr", "DKK": "kr", "SGD": "S$", "BRL": "R$"}
    return symbols.get(str(currency or "").upper(), str(currency or ""))


def render_company_header(f: dict[str, Any]) -> None:
    from html import escape
    general, highlights = profile(f)
    name = escape(str(general.get("Name") or f.get("Symbol", "Company")))
    ticker = escape(str(f.get("Symbol") or general.get("PrimaryTicker", "")))
    exchange = escape(str(general.get("Exchange") or "Exchange n/a"))
    industry = escape(str(general.get("Industry") or "Industry n/a"))
    symbol = currency_symbol(str(general.get("CurrencyCode") or highlights.get("CurrencyCode") or ""))
    current = highlights.get("CurrentPrice")
    previous = highlights.get("PreviousClose")
    change = ((current / previous) - 1) * 100 if current is not None and previous not in (None, 0) else None
    price = fmt_price(current, symbol)
    change_color = "#8ce0c5" if change is not None and change >= 0 else "#ffb1a8"
    change_text = f"{change:+.2f}% vs previous close" if change is not None else "Daily change n/a"
    st.markdown(
        f"<div class='hero'><div><div class='eyebrow'>Equity research workspace</div><h1>{name}</h1><p>{ticker} &nbsp;·&nbsp; {exchange} &nbsp;·&nbsp; {industry}</p></div>"
        f"<div class='hero-price'><div class='hero-price-label'>Last price</div><div class='hero-price-value'>{escape(price)}</div><div class='hero-price-change' style='color:{change_color}'>{escape(change_text)}</div></div></div>",
        unsafe_allow_html=True,
    )
    values = [
        ("Market cap", fmt_money(highlights.get("MarketCapitalization"), symbol)),
        ("52-week high", fmt_price(highlights.get("FiftyTwoWeekHigh"), symbol)),
        ("52-week low", fmt_price(highlights.get("FiftyTwoWeekLow"), symbol)),
        ("Sector", str(general.get("Sector") or "N/A")),
    ]
    cells = "".join(f"<div class='market-cell'><div class='market-label'>{escape(label)}</div><div class='market-value'>{escape(str(value))}</div></div>" for label, value in values)
    st.markdown("<div class='market-banner' style='grid-template-columns:repeat(4,minmax(0,1fr))'>" + cells + "</div>", unsafe_allow_html=True)


def render_ratio_analysis(f: dict[str, Any], peers: list[dict[str, Any]], period: str, thresholds: dict[str, Any], peer_source: str) -> pd.DataFrame:
    from html import escape
    metrics = company_metrics(f, period)
    table, details = metric_table(metrics, thresholds, peers, period)
    score = details["score"]
    favourable = sum(1 for x in details["assessments"].values() if x["status"] == "Favourable")
    peer_names = [f"{p.get('General', {}).get('Name', p.get('Symbol', ''))} ({p.get('Symbol', '')})" for p in peers]
    hover_text = " · ".join(peer_names) if peer_names else "No Yahoo Finance industry peers returned"
    stat_cols = st.columns([1, 1, 1])
    for col, label, value in zip(stat_cols[:2], ["Fundamental score", "Favourable indicators"], [score_label(score["score"]), f"{favourable} / {score['evaluated']}"]):
        col.markdown(f"<div class='dark-stat'><div class='dark-stat-label'>{label}</div><div class='dark-stat-value'>{value}</div></div>", unsafe_allow_html=True)
    with stat_cols[2]:
        with st.container(key=f"industry_company_banner_{period.lower()}"):
            with st.popover(f"INDUSTRY COMPANIES  \n**{len(peers)}**", help=hover_text, width="stretch"):
                if peers:
                    peer_rows = []
                    for peer in peers:
                        g, _ = profile(peer)
                        peer_rows.append({"Company": g.get("Name"), "Ticker": peer.get("Symbol"), "Sector": g.get("Sector"), "Industry": g.get("Industry")})
                    st.dataframe(pd.DataFrame(peer_rows), width="stretch", hide_index=True)
                    st.caption(f"Yahoo Finance industry company sample · {peer_source}. Up to 20 peers; not a complete industry census.")
                else:
                    st.info("Yahoo Finance did not return an industry company sample for this listing.")

    company_label = str(f.get("Symbol") or profile(f)[0].get("Name") or "Company")
    st.markdown("<div class='metric-section-gap'></div>", unsafe_allow_html=True)
    expanded_all = accordion_controls(f"analysis_{period.lower()}")
    for key in METRIC_ORDER:
        benchmark = details["benchmarks"].get(key, {})
        assessment = details["assessments"][key]
        status = assessment["status"]
        value = metrics.get(key)
        peer_median = benchmark.get("median")
        # A status-specific CSS badge is attached to the right of the header.
        # Keep the label plain so Streamlit's Markdown nesting cannot swallow the layout.
        status_slug = status.lower().replace(" ", "_")
        with st.container(key=f"assessment_{period.lower()}_{key}_{status_slug}"):
            with st.expander(f"{METRIC_LABELS[key]}   ·   {format_metric_value(key, value)}", expanded=expanded_all):
                st.write(METRIC_EXPLANATIONS[key])
                st.caption(f"{assessment['comment']}")
                st.markdown(metric_scale_html(key, thresholds[key], [(company_label, value, "#55b7ff", company_label), ("Peer", peer_median, "#19d6a0", "Peer median")]), unsafe_allow_html=True)
    st.session_state["last_analysis"] = {"ticker": f.get("Symbol"), "period": period, "metrics": metrics, "table": table, "score": score["score"]}
    return table


def excel_export(sheets: dict[str, pd.DataFrame]) -> bytes:
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        for name, frame in sheets.items():
            frame.to_excel(writer, sheet_name=name[:31], index=False)
            ws = writer.sheets[name[:31]]
            ws.freeze_panes = "A2"
            ws.auto_filter.ref = ws.dimensions
            for column_cells in ws.columns:
                width = min(max(max(len(str(c.value or "")) for c in column_cells) + 2, 12), 55)
                ws.column_dimensions[column_cells[0].column_letter].width = width
    return output.getvalue()


def pdf_export(title: str, tables: dict[str, pd.DataFrame]) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    output = BytesIO()
    doc = SimpleDocTemplate(output, pagesize=landscape(A4), rightMargin=28, leftMargin=28, topMargin=28, bottomMargin=28)
    styles = getSampleStyleSheet()
    story = [Paragraph(title, styles["Title"]), Paragraph("Yahoo Finance via yfinance · Educational research tool", styles["Normal"]), Spacer(1, 14)]
    for name, frame in tables.items():
        story.append(Paragraph(name, styles["Heading2"]))
        data = [list(frame.columns)] + frame.fillna("").astype(str).values.tolist()
        table = Table(data, repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#14243a")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), .35, colors.HexColor("#dce4ed")),
            ("FONTSIZE", (0, 0), (-1, -1), 7), ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f4f7fa")]),
        ]))
        story.extend([table, Spacer(1, 12)])
    doc.build(story)
    return output.getvalue()


def render_analysis(thresholds: dict[str, Any]) -> None:
    st.markdown("<div class='eyebrow'>Company research</div><h2>Stock analysis</h2>", unsafe_allow_html=True)
    query = st.text_input("Search a company or ticker", key="company_query", placeholder="Start typing: Apple, AAPL, Siemens, Toyota…", help="Suggestions are retrieved from Yahoo Finance as you type (minimum 2 characters).")
    if len(query.strip()) >= 2:
        try:
            if query.strip() != st.session_state.get("last_search_query"):
                st.session_state["search_results"] = cached_search(query.strip())
                st.session_state["last_search_query"] = query.strip()
        except ProviderError as exc:
            st.error(str(exc))
    elif not query.strip():
        st.session_state["search_results"] = []
        st.session_state["last_search_query"] = ""
    results = st.session_state.get("search_results", [])
    if len(query.strip()) >= 2 and results:
        options = {f"{r.get('Name', 'Unknown')} · {r.get('Symbol')} · {r.get('Exchange') or 'Exchange n/a'}": r for r in results if r.get("Symbol")}
        if options:
            labels = list(options)
            current_idx = next((i for i, label in enumerate(labels) if options[label].get("Symbol") == st.session_state.get("analysis_ticker")), 0)
            selected_label = st.selectbox("Yahoo Finance suggestions", labels, index=current_idx, key="company_suggestion")
            if st.button("Analyze selected company", type="primary"):
                selected = options[selected_label]
                st.session_state["analysis_ticker"] = selected.get("Symbol")
                st.session_state["analysis_label"] = selected_label
                st.rerun()
    elif len(query.strip()) >= 2 and not results:
        st.caption("No company suggestions yet. Check the spelling or try a ticker symbol.")

    ticker = st.session_state.get("analysis_ticker")
    if not ticker:
        st.info("Start typing a company name or ticker above to see matching Yahoo Finance listings.")
        return
    try:
        with st.spinner(f"Loading {ticker} fundamentals…"):
            f = get_fundamentals(ticker)
    except ProviderError as exc:
        st.error(str(exc)); return
    render_company_header(f)
    compare_list = st.session_state["compare_selected"]
    compare_help = "Companies currently selected: " + (", ".join(compare_list) if compare_list else "None yet")
    action_cols = st.columns([1, 1, 5])
    if action_cols[0].button("＋ Compare", key="add_to_compare", type="primary", help=compare_help):
        if ticker not in compare_list:
            if len(compare_list) >= 20:
                st.warning("The comparison list is limited to 20 companies. Remove one on Compare Stocks first.")
            else:
                compare_list.append(ticker)
        st.session_state["compare_tickers"] = ", ".join(compare_list)
        st.rerun()
    if action_cols[1].button("☆ Watchlist", key="add_to_watchlist", help="Save this company to your session watchlist"):
        if ticker not in st.session_state["watchlist"]:
            st.session_state["watchlist"].append(ticker)
        st.toast(f"{ticker} added to Watchlist")

    st.subheader("Stock performance")
    ranges = {"1M": "1mo", "3M": "3mo", "6M": "6mo", "1Y": "1y", "5Y": "5y", "Maximum": "max"}
    range_key = f"performance_range_{ticker}"
    if range_key not in st.session_state:
        st.session_state[range_key] = "1Y"
    try:
        chosen_range = st.segmented_control("Period", list(ranges), key=range_key, label_visibility="collapsed") if hasattr(st, "segmented_control") else st.radio("Period", list(ranges), horizontal=True, key=range_key, label_visibility="collapsed")
    except Exception:
        chosen_range = "1Y"
    chosen_range = chosen_range or "1Y"
    history = cached_history(ticker, ranges[chosen_range], "1d")
    if not history.empty and {"date", "close"}.issubset(history.columns):
        chart = history[["date", "close"]].copy()
        chart["date"] = pd.to_datetime(chart["date"], errors="coerce")
        chart["close"] = pd.to_numeric(chart["close"], errors="coerce")
        chart = chart.dropna().sort_values("date").set_index("date")
        chart = chart.rename(columns={"close": "Share price"})
        st.line_chart(chart, width="stretch")
        if len(chart) > 1:
            ret = (float(chart.iloc[-1, 0]) / float(chart.iloc[0, 0]) - 1) * 100
            st.caption(f"{chosen_range} price change: {ret:+.2f}% · Currency: {currency_symbol(profile(f)[0].get('CurrencyCode') or '') or 'as reported by Yahoo Finance'}")
    else:
        st.info("Price history is not available for this listing.")

    general, _ = profile(f)
    industry_key = general.get("IndustryKey")
    country = str(general.get("CountryName") or "").lower()
    region_map = {"united states": "US", "usa": "US", "germany": "DE", "japan": "JP", "united kingdom": "GB", "uk": "GB", "france": "FR", "canada": "CA", "australia": "AU", "hong kong": "HK", "china": "CN", "india": "IN", "brazil": "BR", "switzerland": "CH", "netherlands": "NL", "spain": "ES", "italy": "IT", "sweden": "SE", "singapore": "SG"}
    region = region_map.get(country, "US")
    peers, peer_source = [], f"{region} region"
    if industry_key:
        try:
            peer_rows = cached_industry_companies(str(industry_key), region)
            if peer_rows:
                peer_source = f"Yahoo {peer_rows[0].get('Source', 'industry companies')} · {region} region"
            peer_tickers = [x.get("Symbol") for x in peer_rows if x.get("Symbol") and x.get("Symbol").upper() != ticker.upper()][:20]
            peers = load_many(peer_tickers, progress=bool(peer_tickers)) if peer_tickers else []
        except Exception as exc:
            st.caption(f"Yahoo industry peer data could not be loaded: {exc}")
    else:
        st.caption("Yahoo Finance did not provide an industry key for this company, so an automatic industry comparison is unavailable.")
    ttm_tab, fy_tab = st.tabs(["TTM · Trailing twelve months", "FY · Latest completed year"])
    with ttm_tab:
        ttm_table = render_ratio_analysis(f, peers, "TTM", thresholds, peer_source)
    with fy_tab:
        fy_table = render_ratio_analysis(f, peers, "FY", thresholds, peer_source)
    xlsx = excel_export({"TTM Ratios": ttm_table, "FY Ratios": fy_table})
    d1, d2 = st.columns(2)
    d1.download_button("↓ Export analysis to Excel", xlsx, file_name=f"{ticker}_fundamental_analysis.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    pdf = pdf_export(f"{general.get('Name', ticker)} ({ticker}) — Fundamental Analysis", {"TTM Ratios": ttm_table, "FY Ratios": fy_table})
    d2.download_button("↓ Export analysis to PDF", pdf, file_name=f"{ticker}_fundamental_analysis.pdf", mime="application/pdf")
    st.caption("Yahoo Finance data may be delayed, incomplete or revised. FY valuation multiples use current market values against latest completed FY financials.")


def render_compare(thresholds: dict[str, Any]) -> None:
    st.markdown("<div class='eyebrow'>Relative valuation</div><h2>Compare stocks</h2>", unsafe_allow_html=True)
    tickers = list(dict.fromkeys(st.session_state.get("compare_selected", [])))[:20]
    if not tickers:
        st.info("No companies have been added yet. Find a company on Stock Analysis and select + Compare.")
        return
    remove_chip_row("Click a company to remove it from the comparison", tickers, "compare_selected", "remove_compare")
    tickers = list(dict.fromkeys(st.session_state.get("compare_selected", [])))[:20]
    if not tickers:
        st.info("Your comparison is empty. Add companies from Stock Analysis.")
        return
    period = st.segmented_control("Reporting period", ["TTM", "FY"], default="TTM", key="compare_period") if hasattr(st, "segmented_control") else st.radio("Reporting period", ["TTM", "FY"], horizontal=True)
    companies = load_many(tickers, progress=True)
    rows, metric_rows, metric_values = [], [], {k: [] for k in METRIC_ORDER}
    for f in companies:
        g, h = profile(f); m = company_metrics(f, period)
        assessment = assess_metrics(m, thresholds); score = calculate_score(assessment)
        ticker = str(f.get("Symbol") or g.get("PrimaryTicker") or "")
        rows.append({"Company": g.get("Name"), "Ticker": ticker, "Industry": g.get("Industry"), "Price": fmt_price(h.get("CurrentPrice"), currency_symbol(g.get("CurrencyCode") or h.get("CurrencyCode") or "")), "Screen score": score_label(score["score"])})
        metric_rows.append({"Ticker": ticker, **{METRIC_LABELS[k]: format_metric_value(k, m.get(k)) for k in METRIC_ORDER}})
        for k in METRIC_ORDER:
            metric_values[k].append((ticker, m.get(k), "#" + format((hash(ticker) & 0xFFFFFF), "06x"), ticker))
    if rows:
        overview, ratios = pd.DataFrame(rows), pd.DataFrame(metric_rows)
        st.subheader("Company overview")
        st.dataframe(overview, width="stretch", hide_index=True)
        st.subheader(f"Visual metric comparison · {period}")
        st.caption("Each dot represents one company. The shaded segment shows the preferred threshold or range. Hover over a dot to see its ticker and value.")
        compare_expanded = accordion_controls("compare")
        for key in METRIC_ORDER:
            with st.expander(f"{METRIC_LABELS[key]} · compare {len(companies)} companies", expanded=compare_expanded):
                st.markdown(metric_scale_html(key, thresholds[key], metric_values[key]), unsafe_allow_html=True)
        st.subheader("Comparison table · supporting detail")
        st.dataframe(ratios, width="stretch", hide_index=True)
        st.download_button("Export comparison to Excel", excel_export({"Overview": overview, "Ratios": ratios}), file_name="stock_comparison.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


def render_watchlist() -> None:
    st.markdown("<div class='eyebrow'>Saved for this session</div><h2>Watchlist</h2>", unsafe_allow_html=True)
    watch = st.session_state["watchlist"]
    add = st.text_input("Add Yahoo ticker", placeholder="e.g. NVDA")
    if st.button("Add ticker") and add.strip():
        if add.strip().upper() not in watch: watch.append(add.strip().upper())
        st.rerun()
    if not watch:
        st.info("No saved tickers yet. Add one above to keep a separate session watchlist.")
        return
    remove_chip_row("Click a company to remove it from the watchlist", list(watch), "watchlist", "remove_watch")
    watch = list(st.session_state["watchlist"])
    if not watch:
        return
    companies = load_many(watch)
    rows = []
    for f in companies:
        g, h = profile(f)
        curr = str(g.get("CurrencyCode") or h.get("CurrencyCode") or "")
        symbol = currency_symbol(curr)
        rows.append({"Company": g.get("Name"), "Ticker": f.get("Symbol"), "Price": fmt_price(h.get("CurrentPrice"), symbol), "Market cap": fmt_money(h.get("MarketCapitalization"), symbol), "Industry": g.get("Industry")})
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)


def render_thresholds() -> dict[str, Any]:
    st.markdown("<div class='eyebrow'>Personal screening rules</div><h2>Screening settings</h2>", unsafe_allow_html=True)
    st.caption("Changes apply to screening classifications during this session only. They do not change the underlying ratio calculations.")
    current = {k: dict(v) for k, v in st.session_state["thresholds_session"].items()}
    with st.form("threshold_form"):
        st.subheader("Upper-bound metrics")
        upper_cols = st.columns(4)
        for i, key in enumerate(["pe", "peg", "de", "p_fcf", "ev_ebitda"]):
            current[key]["max"] = upper_cols[i % 4].number_input(f"{METRIC_LABELS[key]} · max", min_value=0.1, max_value=1000.0, value=float(current[key]["max"]), step=0.5, key=f"thr_{key}")
        st.subheader("Preferred ranges")
        range_cols = st.columns(3)
        for i, key in enumerate(["ps", "roe", "cr"]):
            c = range_cols[i]
            c.markdown(f"**{METRIC_LABELS[key]}**")
            current[key]["min"] = c.number_input("Minimum", min_value=0.0, max_value=100.0, value=float(current[key]["min"]), step=0.05 if key == "roe" else 0.1, key=f"min_{key}")
            current[key]["max"] = c.number_input("Maximum", min_value=0.1, max_value=100.0, value=float(current[key]["max"]), step=0.05 if key == "roe" else 0.1, key=f"max_{key}")
        submitted = st.form_submit_button("Save screening rules", type="primary")
    if submitted:
        st.session_state["thresholds_session"] = current
        st.success("Screening rules updated for this session.")
    return st.session_state["thresholds_session"]


def main() -> None:
    init_state()
    with st.sidebar:
        st.markdown("<div style='font-size:1.3rem;font-weight:800;letter-spacing:.02em'>◈ EQUITY<br>INSIGHTS</div><div style='color:#aebed0;font-size:.75rem;margin:.3rem 0 1rem'>STOCK FUNDAMENTALS ANALYZER</div>", unsafe_allow_html=True)
        st.caption("DATA · YAHOO FINANCE / YFINANCE")
        page = st.radio("WORKSPACE", ["Stock Analysis", "Compare Stocks", "Watchlist", "Screening Settings"], key="active_page", label_visibility="collapsed")
        st.divider()
        st.caption("SESSION WORKSPACE")
        st.metric("Companies to compare", len(st.session_state.get("compare_selected", [])))
        st.metric("Watchlist", len(st.session_state["watchlist"]))
        st.caption("Selections and saved research reset when this session ends.")
        st.divider()
        if st.button("Clear session data", width="stretch"):
            for key in ["watchlist", "compare_selected", "fundamentals_session", "search_results", "analysis_ticker", "analysis_label", "comparison_results", "industry_results", "history_result"]:
                st.session_state.pop(key, None)
            st.rerun()
    thresholds = st.session_state["thresholds_session"]
    try:
        if page == "Stock Analysis": render_analysis(thresholds)
        elif page == "Compare Stocks": render_compare(thresholds)
        elif page == "Watchlist": render_watchlist()
        elif page == "Screening Settings": render_thresholds()
    except Exception as exc:
        st.error(f"The page encountered an unexpected error: {exc}")
        st.caption("Try again or clear the session data. If the issue persists, share the error details.")


if __name__ == "__main__":
    main()
