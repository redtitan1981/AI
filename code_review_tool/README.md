# Automated Code Review with LangGraph

A research notebook demonstrating how to build a **production-style automated code review tool** using [LangGraph](https://langchain-ai.github.io/langgraph/). Designed as an educational resource for learners who want to understand agentic workflow patterns.

---

## What You Will Learn

| Pattern | Where |
|---------|-------|
| LLM-as-router (simple / full / error paths) | Step 4 |
| Fan-out parallel agents | Step 6 |
| Fan-in synchronisation + guardrail | Step 7 |
| Structured output + token tracking (`include_raw=True`) | Steps 5, 8 |
| Error propagation in state (no exceptions) | Step 3 |
| Custom reducers for parallel writes | Step 2 |
| State persistence (`flow_state.json`) | Step 13 |
| Streaming real-time updates | Step 16 |
| LangGraph checkpointer (`SqliteSaver`) | Step 20 |

---

## Architecture

```
PR File ──► Router ──► [simple]  ──► Simple Review ────────────────────► Final Decision ──► Answer
                   ├──► [full]   ──► Security Review ─┐
                   │               Quality Analysis  ─┴──► Guardrail ──► Tech Lead ──► Final Decision
                   └──► [error]  ──────────────────────────────────────────────────────► Answer
```

**11 nodes, 3 execution paths, 2 guardrails, parallel agents.**

---

## Sample Output

```
📄 Read PR file: code_changes.txt (1140 chars)
🔀 Router decision: 'full'
⚡ Full review: launching Security Review + Quality Analysis in parallel
🔐 Security Review complete
👨‍💻 Quality Analysis complete
🔗 Aggregate: both agents complete — running output guardrail
🚨 Output guardrail: BLOCKING issue detected — halting review

============================================================
FINAL ANSWER
============================================================
[Full Code Review Tool] REJECT

The pull request contains critical security vulnerabilities including SQL
injection, insecure password handling, and sensitive data exposure.

TOKEN USAGE:
  input_tokens:  1993
  output_tokens: 1271
  total_tokens:  3264
```

---

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Add your OpenAI API key
cp .env.example .env
# then edit .env and paste your key

# 3. Open the notebook
jupyter notebook code_review_tool.ipynb
```

Run cells top to bottom. Each section has a markdown explanation before the code.

---

## Demo Files

| File | Description | Expected verdict |
|------|-------------|-----------------|
| `files/code_changes.txt` | Auth code with SQL injection + PII logging | REJECT (BLOCKING) |
| `files/code_changes_simple.txt` | Import alias rename | APPROVED (simple path) |
| `files/code_changes_needswork.txt` | Style/quality issues only (naming, idioms) — no security holes | REQUEST CHANGES (full, non-blocking) |

---

## Notebook Structure

| Step | Topic |
|------|-------|
| Architecture Overview | Mermaid flowchart + node roles table |
| LangGraph Concepts Primer | State / Nodes / Edges / Reducers |
| Steps 1–2 | Install, imports, shared state schema |
| Steps 3–4 | Read PR file, LLM router |
| Steps 5–9 | Agents, guardrails, Tech Lead synthesis, final decision |
| Steps 10–12 | Graph visualisation, complete graph assembly |
| Steps 13–14 | Run: full BLOCKING + simple paths |
| Steps 15–16 | Audit trail, streaming |
| Steps 17–19 | Error path, non-blocking path, token cost comparison |
| Step 20 | SqliteSaver checkpointer |
| Step 21 | Interactive: review your own diff |
| Step 22 | Unit tests — nodes as pure functions |
| Key Takeaways | Patterns reference + 6 exercises |

---

## Production Modules

The core logic is also available as standalone Python modules for use outside the notebook:

| File | Contents |
|------|----------|
| `state.py` | `PRReviewState`, Pydantic output models, `merge_usage` reducer |
| `nodes.py` | All 13 node and edge functions, ready to import |

---

## Requirements

- Python 3.10+
- OpenAI API key (GPT-4o)
- Dependencies: see `requirements.txt`
