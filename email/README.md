# Email Assistant

Baseline LangGraph email assistant that classifies incoming emails and drafts responses using a two-stage LLM pipeline.

## How it works

```
Incoming email
     |
     v
Triage Router (gpt-4o-mini)
     |
     +-- ignore  --> END
     +-- notify  --> END
     +-- respond --> Response Agent (gpt-4o)
                          |
                          v
                     ReAct loop
                     (reason → tool call → observe → repeat)
                          |
                     write_email / schedule_meeting / check_calendar_availability
```

**Key design decisions:**

| Decision | Rationale |
|----------|-----------|
| Two-model split | Classification is cheap — use gpt-4o-mini; generation is hard — use gpt-4o |
| `with_structured_output(Router)` | Enforces Pydantic schema — no free-text parsing |
| LangGraph `Command` | Router controls routing and state update atomically |
| `add_messages` reducer | Nodes append to message history — never overwrite |

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure API keys

```bash
cp .env.example .env
```

Edit `.env` and add:

```
OPENAI_API_KEY=sk-...
```

### 3. Run the notebook

Open `Baseline Email Assitant.ipynb` in JupyterLab and run all cells top to bottom.

## Files

| File | Description |
|------|-------------|
| `Baseline Email Assitant.ipynb` | Main notebook — full walkthrough with diagrams and learner notes |
| `prompts.py` | Prompt templates for the triage router and response agent |
| `requirements.txt` | Python dependencies |
| `.env.example` | API key template |

## Notebook contents

| Section | What it covers |
|---------|----------------|
| Step 1 | Load API tokens via python-dotenv |
| Step 2 | User profile, triage rules, sample emails |
| Step 3 | Triage router — Router Pydantic schema, structured output, prompt templates |
| Step 4 | Response agent tools — `write_email`, `schedule_meeting`, `check_calendar_availability` |
| Step 5 | Dynamic system prompt — callable `create_prompt(state)` pattern |
| Step 6 | Shared `State` TypedDict, `add_messages` reducer, `triage_router` node with `Command` |
| Step 7 | Graph assembly, `compile()`, test runs with spam and real email |
| Observations | Triage accuracy, hallucination analysis, baseline limitations |

## Limitations (baseline)

- No memory — each email is handled in isolation
- No human-in-the-loop — drafts are sent immediately
- Static triage rules — plain text strings, no learning
- Tools are stubs — no real email or calendar integration
