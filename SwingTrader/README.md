# SwingTrader — POC Notebooks

A LangGraph-based agent that screens NSE equities for swing trade setups, scores them against four technical templates, and produces structured trade candidates with entry zone, stop-loss, and target levels.

---

## Research Question

> Can an LLM agent reliably classify technical chart setups and apply hard-coded reject rules consistently — replacing the subjective "does this look right?" judgement that makes manual screening slow and inconsistent?

**The hypothesis:** Swing trading decisions follow a small set of well-defined templates. An LLM with structured output and explicit reject rules should be able to apply these templates consistently across a large watchlist, faster and more consistently than manual review.

---

## How It Works

### Screening pipeline

```
Watchlist (ticker symbols)
        |
        v
Data Layer (01_data_layer)
  - Fetch OHLCV from yfinance / Kite Connect
  - Compute indicators: EMA-20/50/200, RSI, ATR, Bollinger Bands
  - Compute swing levels (ZigZag 3%)
  - Compute relative strength vs Nifty500
        |
        v
Technical Agent (02_technical_agent)  ← LangGraph node
  - Build structured prompt with price, trend, momentum, volume, RS data
  - gpt-4o classifies into one of four setup templates
  - Apply hard reject rules (below EMA-200, RSI < 40, weak RS)
  - Score setup: trend (0-40) + structure (0-30) + setup (0-20) + volume (0-10)
        |
        ├── REJECTED  ──> Log reason, skip
        └── CANDIDATE ──> Entry zone, stop, T1 target, R:R ratio
                |
                v
        Results table + Plotly chart
```

### The four setup templates

| Template | Condition | Entry | Stop |
|----------|-----------|-------|------|
| `pullback_uptrend` | Price above EMA-200, EMA-20 > EMA-50, pullback to EMA-20 | Near EMA-20 | Below nearest swing low |
| `breakout_base` | Price consolidating near resistance, volume expanding on breakout | Just above resistance | Below base low |
| `mean_reversion_range` | Price in defined range, near support, RSI 40–60 | Near range support | Below support |
| `rs_leader` | Overlay on any of the above; RS > 70th percentile | Per base template | Per base template |

Hard reject rules (applied before LLM, no LLM cost incurred):
- Price below EMA-200 (weekly trend bearish)
- RSI < 35 (momentum weak)
- Relative strength < 50th percentile AND no strong setup
- Volume contraction with no breakout signal

### Scoring rubric

```
Technical score = trend_score + structure_score + setup_score + volume_score

trend_score     (0-40): above EMA-200 (+20), EMA-20 > EMA-50 (+10), weekly uptrend (+10)
structure_score (0-30): clear swing levels (+10), within 5% of support (+10), RS > 60th (+10)
setup_score     (0-20): matches a template (+20), partial match (+10)
volume_score    (0-10): expanding volume on setup (+10), neutral (0), contraction (-5)

Candidates: score >= 60 and not rejected
```

---

## Setup

### Prerequisites
- Python 3.11+
- OpenAI API key (for `gpt-4o` classification)
- Kite Connect credentials (optional — notebooks fall back to yfinance automatically)

### 1. Clone the repo

```bash
git clone https://github.com/redtitan1981/AI.git
cd AI/SwingTrader
```

### 2. Create and activate a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate      # macOS / Linux
# venv\Scripts\activate       # Windows
```

Your prompt should change to `(venv)`. Verify:

```bash
which python   # should print: .../SwingTrader/venv/bin/python
```

> **Python version:** Run `python3 --version`. If it prints below 3.11, use a full path to a newer interpreter:
> ```bash
> /opt/homebrew/bin/python3.12 -m venv venv
> ```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

This installs all packages listed in `requirements.txt` into the local `venv`. The `venv/` directory is gitignored — each contributor creates their own.

### 4. Configure environment variables

```bash
cp .env.example .env
```

Open `.env` and fill in values:

```
# Required
OPENAI_API_KEY=sk-...

# Optional — LangSmith tracing
LANGCHAIN_API_KEY=ls__...

# Optional — Kite Connect live feed (Phase 7+)
KITE_API_KEY=...
KITE_SECRET=...
KITE_ACCESS_TOKEN=...    # expires daily at ~08:00 IST
```

> The `.env` file can live in `SwingTrader/` or any parent directory — `load_dotenv()` searches up to 4 levels.

### 5. Verify setup

```bash
jupyter lab notebooks/00_setup.ipynb
```

Run all cells top to bottom. All checks must pass (green output) before proceeding to other notebooks. The setup notebook verifies:
- Python version
- All required packages installed and importable
- `OPENAI_API_KEY` present and valid (makes a test API call)
- yfinance data fetch works
- Kite Connect config (skipped gracefully if not configured)

---

## Notebooks

### `00_setup.ipynb` — Environment verification

Run this first, every time you set up a new environment. It is a diagnostic tool, not a tutorial.

Checks performed:
- Python 3.11+ version gate
- Import test for all required packages
- OpenAI API connectivity test (sends a minimal prompt, verifies response)
- yfinance data fetch test (downloads 5 days of NIFTY data)
- Optional Kite Connect token validation

### `01_data_layer.ipynb` — Data fetching and indicator computation

Builds the data pipeline that feeds the technical agent.

Topics covered:
- **Data sources:** yfinance (research, free) vs Kite Connect (live, reliable, requires subscription). The notebooks use a unified `fetch_ohlcv(symbol, source)` interface — switching sources requires changing one parameter.
- **OHLCV processing:** Adjusting for NSE symbol format (`INFY.NS` for yfinance, `NSE:INFY` for Kite)
- **Technical indicators** via `pandas-ta`:
  - Trend: EMA-20, EMA-50, EMA-200 and their slopes
  - Momentum: RSI(14)
  - Volatility: ATR(14), Bollinger Bands(20, 2)
  - Structure: ZigZag(3%) swing highs and lows
- **Relative strength:** 13-week return vs Nifty500, expressed as a percentile rank across the universe
- **Data validation:** Checks for missing bars, adjusted close discrepancies, and stale data

### `02_technical_agent.ipynb` — LangGraph classification agent

The core research notebook. Builds the LangGraph agent that classifies setups.

Topics covered:
- **Prompt construction:** Converting raw indicator values into a structured natural-language prompt. The prompt includes price, trend signals, momentum, volume context, swing levels, and RS rating.
- **Structured output:** `with_structured_output(SetupAnalysis)` forces the LLM to return a validated Pydantic object with fields for `direction`, `setup_template`, `technical_score`, `entry_zone`, `stop_loss`, `target`, `rr_ratio`, `reasoning`, and `rejected`.
- **Hard reject rules:** Applied as Python logic before the LLM call for cost efficiency. If a symbol fails a reject rule, no LLM call is made.
- **LangGraph node:** The agent is a single `StateGraph` node that iterates over the watchlist, calls the LLM per symbol, and accumulates results.
- **Visualisation:** Plotly candlestick chart with EMA overlays, volume bars, and entry/stop/target annotations.

### `03_poc_pipeline.ipynb` — End-to-end screening pipeline

Combines `01` and `02` into a full screening run across a multi-symbol watchlist.

Topics covered:
- Running the full pipeline: fetch → compute → classify → collect
- Results table: symbol, setup template, technical score, RS rating, entry zone, stop, T1, R:R
- Sorting candidates by technical score and RS rating
- Exporting results to `notebooks/results/` as CSV (gitignored, so results stay local)
- Understanding why all candidates may be rejected (market regime check)

---

## Data Sources

### yfinance (default for research)
- Free, no authentication required
- 1-day minimum resolution
- Data quality acceptable for EOD swing trading research
- Symbol format: `INFY.NS`, `RELIANCE.NS`

### Kite Connect (optional, for live/paper trading)
- Zerodha's official API — reliable, institutional-quality data
- Supports tick-level and minute-level data
- **Access token expires daily at ~08:00 IST** — regenerate using Cell 7 in `00_setup.ipynb`
- Requires a Zerodha trading account and Kite Connect subscription (~₹2000/month)
- Symbol format: `NSE:INFY`, `NSE:RELIANCE`

The data layer abstracts over both — set `DATA_SOURCE=kite` in `.env` to switch.

---

## Kite Connect Token Refresh

The Kite access token expires at the start of each trading day (~08:00 IST). To refresh:

1. Open `notebooks/00_setup.ipynb`
2. Run Cell 7 — it opens the Kite login URL, handles the OAuth callback via `pyotp` (if TOTP is configured), and saves the new token to `.env`
3. Re-run any notebook that uses Kite data

For automated daily refresh, set `KITE_TOTP_SECRET` in `.env` — Cell 7 will generate the TOTP automatically without manual intervention.

---

## Results

Results from screening runs are saved to `notebooks/results/` as CSV files. This directory is gitignored — results stay local and are not committed.

Example output:

```
Symbol     Setup                  Score  RS    Entry low   Stop       T1         R:R
TATAMOTORS pullback_uptrend       72     68.4  ₹912.50     ₹887.30    ₹985.00    2.9x
HCLTECH    breakout_base          65     71.2  ₹1,620.00   ₹1,578.00  ₹1,750.00  3.1x
ICICIBANK  rs_leader+pullback     78     82.1  ₹1,245.00   ₹1,198.00  ₹1,380.00  2.9x
```

---

## Notes

- **Kite Connect** is optional during research phases — all notebooks fall back to yfinance automatically when Kite credentials are absent.
- **`venv/`** is gitignored — each contributor creates their own local virtual environment.
- **`notebooks/results/`** is gitignored — screening outputs are local only.
- **Python 3.11+** is required; `pandas-ta` and `langgraph` have compatibility issues with older versions.
- **LangSmith tracing** is strongly recommended during development — it lets you inspect every LLM prompt and response in the LangSmith UI, which is essential for debugging classification errors.

---

## Dependencies

| Package | Why it's needed |
|---------|----------------|
| `langchain`, `langchain-openai`, `langchain-core` | LLM calls and tool framework |
| `langgraph` | `StateGraph` for the screening pipeline node |
| `langsmith` | Tracing and debugging LLM calls |
| `yfinance` | Free EOD market data |
| `pandas`, `pandas-ta` | OHLCV processing and technical indicators |
| `numpy` | Numerical operations |
| `pydantic` | `SetupAnalysis` structured output schema |
| `plotly` | Interactive candlestick charts with annotations |
| `scipy` | Percentile rank computation for RS rating |
| `python-dotenv` | Load API keys from `.env` |
| `pyotp` | TOTP generation for automated Kite token refresh |
| `apscheduler` | Scheduled daily screening runs (Phase 3+) |
| `python-telegram-bot` | Trade candidate alerts via Telegram (Phase 3+) |
| `sqlalchemy`, `alembic` | Persistent results store (Phase 3+) |
| `tenacity` | Retry logic for API calls |
