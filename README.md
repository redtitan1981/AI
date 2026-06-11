# AI Research Notebooks

A mono-repo of Jupyter notebooks exploring practical LLM agent architectures across three research areas: voice agents, email automation, and algorithmic trading. Each project is self-contained with its own dependencies, environment config, and README.

---

## Research Themes

All three projects share a common investigation thread:

> **How do you build LLM-powered systems that are cost-efficient, reliable, and production-ready — not just demo-worthy?**

| Theme | Voice Agents | Email Assistant | SwingTrader |
|-------|-------------|-----------------|-------------|
| Cost efficiency | Small model for VAD/STT gating; skip LLM when no speech | gpt-4o-mini for triage; gpt-4o only when needed | gpt-4o only on screened candidates |
| Reliability | Streaming pipeline with fallback; VAD prevents hallucinated transcriptions | Pydantic-constrained output; no free-text parsing | Structured output; hard reject rules before LLM |
| Production gap | Stub WebRTC transport → real LiveKit session | Stub tools → real SMTP/Calendar API | yfinance → Kite Connect live feed |

---

## Projects

### 1. Voice Agents — [`voice agents/`](voice%20agents/)

Research into real-time voice agent architecture: how to chain VAD, STT, LLM, and TTS into a low-latency conversational pipeline, and how to measure and reduce end-to-end latency at each stage.

| Notebook | What you'll learn |
|----------|-------------------|
| [Voice Agent Components](voice%20agents/Voice%20Agent%20Components.ipynb) | How each stage works, how to wire them together with LiveKit Agents, voice-specific prompt constraints |
| [Optimizing Latency](voice%20agents/Optimizing%20Latency.ipynb) | How to instrument and profile a streaming pipeline, identify the dominant bottleneck, and apply targeted optimisations |

**Stack:** LiveKit Agents · OpenAI Whisper (STT) · GPT-4o (LLM) · ElevenLabs (TTS) · Silero (VAD)

**Quick start:**
```bash
pip install -r requirements.txt
cp .env.example .env    # fill in OPENAI_API_KEY and ELEVEN_API_KEY
```

See [`voice agents/README.md`](voice%20agents/README.md) for the full setup guide and architecture explanation.

---

### 2. Email Assistant — [`email/`](email/)

A two-stage LangGraph agent that triages incoming email with a cheap model and routes only actionable emails to a capable ReAct agent. Designed as a baseline to measure before adding memory, human-in-the-loop, and grounding in later lessons.

| Notebook | What you'll learn |
|----------|-------------------|
| [Baseline Email Assistant](email/Baseline%20Email%20Assitant.ipynb) | LangGraph StateGraph, structured LLM output, ReAct tool loops, `Command`-based routing, `add_messages` reducer |

**Stack:** LangGraph · LangChain · GPT-4o-mini (triage) · GPT-4o (response) · Pydantic

**Quick start:**
```bash
pip install -r email/requirements.txt
cp email/.env.example email/.env    # fill in OPENAI_API_KEY
```

See [`email/README.md`](email/README.md) for architecture details, key concepts, and a section-by-section notebook guide.

---

### 3. SwingTrader — [`SwingTrader/`](SwingTrader/)

A LangGraph agent that screens NSE equities for swing trade setups, scores them against four technical templates, and produces structured trade candidates with entry, stop, and target levels.

| Notebook | What you'll learn |
|----------|-------------------|
| `00_setup.ipynb` | Environment verification — confirms all dependencies and API keys before you run anything |
| `01_data_layer.ipynb` | Fetching OHLCV data from yfinance / Kite Connect, computing technical indicators with pandas-ta |
| `02_technical_agent.ipynb` | LangGraph agent that classifies setups, scores them, and applies hard reject rules |
| `03_poc_pipeline.ipynb` | Full end-to-end screening pipeline across a watchlist |

**Stack:** LangGraph · LangChain · GPT-4o · pandas-ta · yfinance · Kite Connect (optional) · Plotly

**Quick start:**
```bash
cd SwingTrader
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env    # fill in OPENAI_API_KEY; Kite keys optional
```

See [`SwingTrader/README.md`](SwingTrader/README.md) for full setup instructions, Kite Connect configuration, and notebook progression guide.

---

## Prerequisites

All projects require Python 3.11+ and a Jupyter environment. Each project manages its own virtual environment and `requirements.txt`.

| Requirement | Voice Agents | Email Assistant | SwingTrader |
|-------------|:-----------:|:---------------:|:-----------:|
| Python 3.11+ | Yes | Yes | Yes |
| OpenAI API key | Yes | Yes | Yes |
| ElevenLabs API key | Yes | — | — |
| Kite Connect credentials | — | — | Optional |

---

## Repository Structure

```
AI/
├── voice agents/                        # Real-time voice pipeline research
│   ├── Voice Agent Components.ipynb
│   ├── Optimizing Latency.ipynb
│   ├── images/                          # Architecture diagrams
│   └── README.md
│
├── email/                               # LangGraph email assistant
│   ├── Baseline Email Assitant.ipynb
│   ├── prompts.py                       # Triage and agent prompt templates
│   ├── requirements.txt
│   ├── .env.example
│   └── README.md
│
├── SwingTrader/                         # NSE swing trading agent
│   ├── notebooks/
│   │   ├── 00_setup.ipynb
│   │   ├── 01_data_layer.ipynb
│   │   ├── 02_technical_agent.ipynb
│   │   ├── 03_poc_pipeline.ipynb
│   │   └── results/                     # Output files (gitignored)
│   ├── requirements.txt
│   ├── .env.example
│   └── README.md
│
├── requirements.txt                     # Voice agents dependencies (root-level)
├── .env.example                         # Voice agents API keys (root-level)
└── README.md
```

---

## Common Patterns Across Projects

These design patterns appear in multiple projects and are worth understanding before diving in:

**Structured LLM output (Pydantic + `with_structured_output`)**
Forces the LLM to return a validated Python object rather than free text. Used in the email triage router and the SwingTrader setup classifier to eliminate parsing fragility.

**Two-model cost splitting**
A cheap, fast model handles classification or filtering; an expensive, capable model handles generation or reasoning. Keeps cost proportional to task complexity.

**LangGraph StateGraph**
A directed graph where nodes are Python functions that read from and write to a shared `State` TypedDict. Used in both the email assistant and SwingTrader agent. The `add_messages` reducer is a key concept: it appends to a message list rather than replacing it, making multi-turn agents safe.

**Stub → real implementation pattern**
All external integrations (email sending, calendar, trading API) start as stubs that return hardcoded strings. This lets you validate the agent's reasoning before wiring up real infrastructure.
