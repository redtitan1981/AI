# AI Research Notebooks

A collection of Jupyter notebooks exploring LLM agent architectures — voice agents, email automation, and algorithmic trading.

---

## Projects

### 1. Voice Agents — [`voice agents/`](voice%20agents/)

Real-time voice agent built on [LiveKit Agents](https://docs.livekit.io/agents/).

| Notebook | Description |
|----------|-------------|
| [Voice Agent Components](voice%20agents/Voice%20Agent%20Components.ipynb) | Core pipeline: VAD → STT → LLM → TTS |
| [Optimizing Latency](voice%20agents/Optimizing%20Latency.ipynb) | Per-stage latency measurement and reduction |

**Pipeline:** `VAD (Silero) → STT (OpenAI Whisper) → LLM (GPT-4o) → TTS (ElevenLabs)`

**Quick start:**
```bash
pip install -r requirements.txt
cp .env.example .env   # add OPENAI_API_KEY and ELEVEN_API_KEY
```

See [`voice agents/README.md`](voice%20agents/README.md) for details.

---

### 2. Email Assistant — [`email/`](email/)

Baseline LangGraph email assistant with a two-stage triage + ReAct response pipeline.

| Notebook | Description |
|----------|-------------|
| [Baseline Email Assistant](email/Baseline%20Email%20Assitant.ipynb) | gpt-4o-mini triage router + gpt-4o response agent with tool use |

**Pipeline:** `Incoming email → Triage Router (gpt-4o-mini) → [ignore / notify / respond] → Response Agent (gpt-4o) → write_email / schedule_meeting`

**Quick start:**
```bash
pip install -r email/requirements.txt
cp email/.env.example email/.env   # add OPENAI_API_KEY
```

See [`email/README.md`](email/README.md) for details.

---

### 3. SwingTrader — [`SwingTrader/`](SwingTrader/)

LangGraph-based swing trading agent for NSE equities.

| Notebook | Description |
|----------|-------------|
| `00_setup.ipynb` | Environment and dependency verification |
| `01_data_layer.ipynb` | yfinance / Kite data fetching and OHLC processing |
| `02_technical_agent.ipynb` | Technical indicator agent (pandas-ta + LangGraph) |
| `03_poc_pipeline.ipynb` | End-to-end POC pipeline |

**Quick start:**
```bash
cd SwingTrader
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add OPENAI_API_KEY
```

See [`SwingTrader/README.md`](SwingTrader/README.md) for full setup and Kite Connect instructions.

---

## Repository Structure

```
AI/
├── voice agents/
│   ├── Voice Agent Components.ipynb
│   ├── Optimizing Latency.ipynb
│   ├── images/
│   └── README.md
├── email/
│   ├── Baseline Email Assitant.ipynb
│   ├── prompts.py
│   ├── requirements.txt
│   ├── .env.example
│   └── README.md
├── SwingTrader/
│   ├── notebooks/
│   ├── requirements.txt
│   ├── .env.example
│   └── README.md
├── requirements.txt      # voice agents dependencies
├── .env.example          # voice agents API keys
└── README.md
```
