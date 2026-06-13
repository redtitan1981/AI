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
| LangGraph checkpointer (`SqliteSaver`) | Step 20 |
| Streaming real-time updates | Step 16 |

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

## Quick Start

```bash
# 1. Install dependencies
pip install langgraph langchain-openai langchain-core python-dotenv grandalf

# 2. Add your OpenAI API key
echo "OPENAI_API_KEY=sk-..." > .env

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
| LangGraph Concepts Primer | State / Nodes / Edges / Reducers + CrewAI mapping |
| Steps 1-2 | Install, imports, shared state schema |
| Steps 3-4 | Read PR file, LLM router |
| Steps 5-9 | Agents, guardrails, Tech Lead synthesis, final decision |
| Steps 10-12 | Subgraph visualisation, complete graph assembly |
| Steps 13-14 | Run: full BLOCKING + simple paths |
| Steps 15-16 | Audit trail, streaming |
| Steps 17-19 | Error path, non-blocking path, token cost comparison |
| Step 20 | SqliteSaver checkpointer |
| Step 21 | Interactive: review your own diff |
| Key Takeaways | Patterns reference + 6 exercises |

---

## Requirements

- Python 3.10+
- OpenAI API key (GPT-4o)
- See `pip install` command above
