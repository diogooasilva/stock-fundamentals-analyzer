"""Editable financial screening thresholds and display metadata."""

METRIC_ORDER = ["pe", "ps", "peg", "de", "roe", "p_fcf", "ev_ebitda", "cr"]

METRIC_LABELS = {
    "pe": "P/E ratio",
    "ps": "Price / Sales",
    "peg": "PEG ratio",
    "de": "Debt / Equity",
    "roe": "Return on Equity",
    "p_fcf": "Price / Free Cash Flow",
    "ev_ebitda": "EV / EBITDA",
    "cr": "Current Ratio",
}

# Format styles: "multiple" renders x, "percent" renders percent, "number" renders raw.
METRIC_FORMATS = {
    "pe": "multiple",
    "ps": "multiple",
    "peg": "multiple",
    "de": "multiple",
    "roe": "percent",
    "p_fcf": "multiple",
    "ev_ebitda": "multiple",
    "cr": "multiple",
}

# The screening cut-offs requested by the user. Boundaries are inclusive where stated.
THRESHOLDS = {
    "pe": {"kind": "upper", "max": 20.0},
    "ps": {"kind": "range", "min": 1.0, "max": 2.0},
    "peg": {"kind": "upper", "max": 1.0},
    "de": {"kind": "upper", "max": 1.0},
    "roe": {"kind": "range", "min": 0.15, "max": 0.20},
    "p_fcf": {"kind": "upper", "max": 10.0},
    "ev_ebitda": {"kind": "upper", "max": 10.0},
    "cr": {"kind": "range", "min": 1.0, "max": 2.0},
}
