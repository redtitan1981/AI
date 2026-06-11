# SwingTrader — POC Notebooks

LangGraph-based swing trading agent for NSE equities.

## Setup

### 1. Clone the repo

```bash
git clone https://github.com/redtitan1981/AI.git
cd AI/SwingTrader
```

### 2. Create and activate a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate   # run this every time you open a new Terminal for this project
```

Your prompt should change to `(venv)`. Confirm:
```bash
which python   # should print: .../SwingTrader/venv/bin/python
```

> **Note:** If `python3 --version` is below 3.11, use a full path to a newer Python:
> `path/to/python3.12 -m venv venv`

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and add at minimum:

```
OPENAI_API_KEY=sk-...
```

The `.env` file can live in `SwingTrader/` or any parent directory — the notebooks search up to 4 levels.

### 5. Verify setup

Open and run `notebooks/00_setup.ipynb` top to bottom. All checks must pass before proceeding.

## Notebooks

| Notebook | Contents |
|---|---|
| `00_setup.ipynb` | Environment and dependency verification |
| `01_data_layer.ipynb` | yfinance / Kite data fetching and OHLC processing |
| `02_technical_agent.ipynb` | Technical indicator agent (pandas-ta + LangGraph) |
| `03_poc_pipeline.ipynb` | End-to-end POC pipeline |

## Notes

- **Kite Connect** is optional for research phases — notebooks fall back to yfinance automatically.
- **KITE_ACCESS_TOKEN** expires daily at ~08:00 IST. Regenerate using Cell 7 in `00_setup.ipynb`.
- Results are saved to `notebooks/results/` (gitignored).
- `venv/` is gitignored — each contributor creates their own local venv.
