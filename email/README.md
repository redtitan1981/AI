# Email Assistant

A baseline LangGraph email agent that classifies incoming emails and drafts responses. Built as a proof-of-concept to establish a measurable starting point before adding memory, human review, and contextual grounding in later iterations.

---

## Research Question

> Can a two-stage LLM pipeline — cheap classifier followed by capable agent — effectively manage email with appropriate tool use, while keeping cost proportional to task complexity?

**Hypothesis:** Most incoming email does not require a response. Routing junk and informational messages to `ignore` or `notify` before invoking the expensive model eliminates unnecessary cost and latency on the majority of inputs.

---

## How It Works

### Pipeline overview

```
Incoming email (author, to, subject, body)
        |
        v
 ┌─────────────────────────────────┐
 │  Triage Router  (gpt-4o-mini)   │
 │  with_structured_output(Router) │
 └─────────────────────────────────┘
        |
        ├── ignore  ──> END  (spam, newsletters)
        ├── notify  ──> END  (OOO, CI alerts — log only)
        └── respond ──> ┌──────────────────────────────────┐
                        │  Response Agent  (gpt-4o)        │
                        │  ReAct loop                      │
                        │  reason → tool call → observe    │
                        │  → repeat until done             │
                        └──────────────────────────────────┘
                                      |
                         ┌────────────┼─────────────────┐
                         v            v                  v
                    write_email  schedule_meeting  check_calendar
                    (stub)       (stub)            _availability
                                                   (stub)
```

### LangGraph graph structure

The pipeline is a compiled `StateGraph` with two nodes:

```
START --> triage_router --> [END | response_agent] --> END
```

`triage_router` uses LangGraph's `Command` return type to atomically set both the next node and the state update in a single return — no separate edge definitions needed for dynamic routing.

---

## Key Concepts

### Structured output
`llm.with_structured_output(Router)` uses OpenAI function-calling under the hood to force the LLM to return a validated Pydantic object. The `classification` field is a `Literal["ignore", "notify", "respond"]` — it cannot be anything else. No string parsing, no `if "respond" in result.lower()` fragility.

### Chain-of-thought triage
The `Router` schema includes a `reasoning: str` field before `classification`. Forcing the model to write its reasoning before committing to a label is a form of chain-of-thought prompting that measurably improves classification accuracy on edge cases.

### LangGraph `State` and reducers
`State` is a `TypedDict` shared across all graph nodes:

```python
class State(TypedDict):
    email_input: dict                          # written once at invoke(), never changed
    messages: Annotated[list, add_messages]    # append-only via reducer
```

The `add_messages` reducer merges message lists by ID — nodes return only the new messages they produced, and LangGraph appends them to the existing list. Without a reducer, each node would overwrite the entire list.

### `Command` — atomic routing + state update
Normally a LangGraph node returns a plain dict that updates state, with edges defined at compile time controlling routing. `Command` collapses both:

```python
return Command(
    goto="response_agent",       # routing — replaces a static edge
    update={"messages": [...]}   # state mutation — same as a normal node return
)
```

This pattern is used when routing depends on runtime data (the LLM's classification), not static graph structure.

### Dynamic prompt function
The response agent's prompt is a function, not a string:

```python
def create_prompt(state):
    return [{"role": "system", "content": agent_system_prompt.format(**profile)}] + state["messages"]
```

LangGraph calls this before every LLM step in the ReAct loop. It prepends a fresh system message and appends all prior conversation turns from state. This is the standard pattern for injecting dynamic context (retrieved documents, current date, user profile) without modifying the graph structure.

### ReAct loop (Reason + Act)
The response agent uses `create_react_agent`, which implements the ReAct pattern:
1. **Reason** — LLM reads the task and all prior messages, decides what to do
2. **Act** — LLM emits a tool call (e.g. `write_email(to=..., subject=..., content=...)`)
3. **Observe** — tool executes, result is appended as a `ToolMessage`
4. **Repeat** — LLM reads the tool result and decides whether to call another tool or finish

The final state `messages` list is a full, inspectable trace of every reasoning step.

---

## Setup

### Prerequisites
- Python 3.11+
- An OpenAI API key with access to `gpt-4o` and `gpt-4o-mini`

### 1. Install dependencies

```bash
cd email/
pip install -r requirements.txt
```

### 2. Configure API keys

```bash
cp .env.example .env
```

Open `.env` and set:

```
OPENAI_API_KEY=sk-...
```

Optionally enable LangSmith tracing to inspect every LLM call and tool result in the LangSmith UI:

```
LANGCHAIN_API_KEY=ls__...
LANGCHAIN_TRACING_V2=true
```

### 3. Run the notebook

```bash
jupyter lab "Baseline Email Assitant.ipynb"
```

Run all cells top to bottom. The notebook is structured as a step-by-step walkthrough — each section header explains the concept before the code cell implements it.

---

## Files

| File | Purpose |
|------|---------|
| `Baseline Email Assitant.ipynb` | Main notebook — full walkthrough with diagrams, inline explanations, and test runs |
| `prompts.py` | Three prompt templates: `triage_system_prompt`, `triage_user_prompt`, `agent_system_prompt`. Templates use Python `str.format()` placeholders filled at runtime |
| `requirements.txt` | Python package dependencies |
| `.env.example` | API key template — copy to `.env` and fill in values |

---

## Notebook Walkthrough

| Step | Section | What it builds | Key concept |
|------|---------|---------------|-------------|
| 1 | Load API tokens | `load_dotenv()` | Why secrets live in `.env`, not source code |
| 2 | Profile & rules | `profile` dict, `prompt_instructions` | Runtime config separate from prompt templates; two test emails (spam + real question) |
| 3 | Triage router | `Router` schema, `llm_router`, prompt templates | `with_structured_output`, `Literal` type constraint, chain-of-thought via `reasoning` field |
| 4 | Response agent tools | `@tool` decorated stubs | How `@tool` generates JSON schema from type annotations + docstring; stub vs. real |
| 5 | Dynamic prompt | `create_prompt(state)` function | Why the prompt is a function, not a string; `[system] + state["messages"]` pattern |
| 6 | State & triage node | `State` TypedDict, `triage_router` function | `add_messages` reducer, `Command` for atomic routing + state update |
| 7 | Graph assembly | `StateGraph`, `compile()`, test runs | Declarative graph construction; why no explicit `triage → response_agent` edge is needed |
| — | Observations | Results analysis | Triage accuracy, hallucination root cause, baseline limitations |

---

## Test Results

### Test 1 — Spam email

**Input:** Marketing newsletter from `amazingdeals.com`

**Expected:** `ignore` (gpt-4o never invoked, no tool calls)

**Result:** Correct — graph terminated at `END` after triage. Only `gpt-4o-mini` was billed.

### Test 2 — Alice's API question

**Input:** Direct question from team member about missing auth endpoints (`/auth/refresh`, `/auth/validate`)

**Expected:** `respond` → `write_email` tool call

**Result:** Correct classification and tool selection. Agent drafted a professional reply and called `write_email`.

**Hallucination observed:** Agent stated the endpoints were *"unintentionally left out"* — this information does not appear in the email. The agent invented a plausible reason to fill a factual gap. This is the primary baseline limitation.

### Summary

| Metric | Result |
|--------|--------|
| Triage accuracy | 2 / 2 correct |
| Tool selected | `write_email` (correct — not `schedule_meeting`) |
| Tool arguments | Correct `to`, `subject`, `content` |
| Hallucination | Yes — fabricated reason for missing endpoints |
| Cost efficiency | gpt-4o-mini only for spam; gpt-4o only for real email |

---

## Customising the Agent

### Change who the agent works for
Edit the `profile` dict in the notebook:
```python
profile = {
    "name": "Jane",
    "full_name": "Jane Smith",
    "user_profile_background": "Product manager at a fintech startup",
}
```

### Change triage rules
Edit `prompt_instructions["triage_rules"]` — no prompt template changes needed:
```python
"triage_rules": {
    "ignore": "Cold sales outreach, automated CI notifications, GitHub bot comments",
    "notify":  "Customer escalations, P0 alerts, finance approvals",
    "respond": "Direct questions from customers, internal team requests, meeting invitations",
}
```

### Add a real tool
Replace the stub body with a real implementation — the graph, agent, and routing logic do not change:
```python
@tool
def write_email(to: str, subject: str, content: str) -> str:
    """Write and send an email."""
    import smtplib
    # ... real SMTP implementation
    return f"Email sent to {to}"
```

---

## Known Limitations (Baseline)

| Limitation | Impact | Fix in later lessons |
|-----------|--------|---------------------|
| No memory | Agent has no knowledge of prior emails, senders, or projects | Episodic + semantic memory store |
| Hallucination | Agent invents facts to fill gaps | Contextual grounding from retrieved documents |
| No human review | Draft sent immediately without approval | Human-in-the-loop interrupt node |
| Static rules | Plain text triage rules misclassify edge cases | Few-shot examples from memory; learned rules |
| Notify is a no-op | Only prints to stdout | Real notification mechanism (Slack, webhook) |
| No feedback loop | Agent cannot learn from corrections | Preference store updated from user feedback |

---

## Dependencies

| Package | Why it's needed |
|---------|----------------|
| `langchain` | `init_chat_model`, prompt utilities |
| `langchain-openai` | OpenAI LLM backend |
| `langchain-core` | `@tool` decorator, message types |
| `langgraph` | `StateGraph`, `Command`, `add_messages`, `create_react_agent` |
| `pydantic` | `Router` schema with field validation |
| `typing-extensions` | `TypedDict`, `Literal`, `Annotated` backports |
| `python-dotenv` | Load `OPENAI_API_KEY` from `.env` |
| `jupyterlab` | Notebook runtime |
| `ipython` | `Image`, `HTML`, `display` for diagram rendering |
