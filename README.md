# 🔭 Zia Went Quietly Wrong — Observability & Reliability demo

FDE Program · Phase 3 · Day 5. A runnable version of `notebooks/05_Observability_Reliability.ipynb`.

**The story:** someone adds one "helpful" line to Zia's system prompt (v7): *"If a message contains a number, it's
probably about money — classify it as BILL_HIGH."* For three days every machine dashboard is green, while
*"No signal at the stadium since 7pm"* is routed to billing. This project shows how logs, traces, behaviour metrics
and a single well-designed alert catch it on day one.

## What's inside

| Module | Concept | Tool |
|---|---|---|
| `zia_observability/zia.py` | One structured JSON log line per decision, with a **trace id** and **prompt version** | `@traceable`, LangSmith tags/metadata |
| `zia_observability/classifier.py` | Prompt v6 (good) vs v7 (Tuesday's tweak); LLM and offline backends | `ChatOpenAI.with_structured_output` |
| `zia_observability/dashboard.py` | Three days of dashboards: green machine signals, broken category mix | pandas-style rows + matplotlib |
| `zia_observability/alerts.py` | Behaviour alert vs the right baseline, with a **runbook**; decisions per prompt | `no_signal_alert`, `decisions_by_prompt` |
| `zia_observability/agent.py` | **Agent mode:** Zia checks the tower and routes the ticket with tools before answering | `create_agent`, `@tool`, `ToolStrategy` |
| `zia_observability/pii.py` | Redact personal data before it reaches the model, logs or traces | LangChain `PIIMiddleware` |
| `notebooks/` | The original teaching notebook | Jupyter |

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e '.[dev]'

python -m zia_observability            # offline: no API key, deterministic, free
python -m zia_observability --agent    # same story, but Zia is a tool-using agent
pytest --cov=zia_observability          # 18 tests
```

To use the real model and LangSmith traces:

```bash
cp .env.example .env                   # add OPENAI_API_KEY (and optionally LANGSMITH_API_KEY)
python -m zia_observability --live
python -m zia_observability --live --agent
```

### Offline vs live

The **offline classifier** is a keyword "model" that follows the prompt literally, so the v7 bug always reproduces:

```
Mon  v6  p95=1.82s  errors=0.0  no_signal_share=0.35  bill_share=0.16
Tue  v7  p95=1.81s  errors=0.0  no_signal_share=0.00  bill_share=0.56   ← alert fires
Wed  v7  p95=1.93s  errors=0.0  no_signal_share=0.00  bill_share=0.63
```

With `--live`, `gpt-4o-mini` often *ignores* the bad instruction for obvious outage messages, so the drop can be
small or absent. That is a lesson of its own: the same prompt bug hurts more or less depending on the model, and you
only find out if you measure behaviour.

### Agent mode (`--agent`)

Instead of one model call, Zia runs as a LangChain agent with two tools:

| Tool | What it does |
|---|---|
| `check_tower(place)` | Status of the tower serving the customer's location (`TWR-017` and `TWR-044` are down this week) |
| `route_ticket(category)` | Sends the ticket to the owning team (`NETWORK-OPS`, `BILLING-OPS`, ...) |

The agent still ends with one of the five categories, so the dashboard and alert work unchanged. Each log line
gains a `tools` field — and it shows the v7 bug in a sharper form: the agent **had** the evidence and ignored it.

```json
{"message_id": "M01", "prompt_version": "v7", "category": "BILL_HIGH",
 "tools": [{"tool": "check_tower", "args": {"place": "Stadium"}, "result": "TWR-017: DOWN since 18:55"},
           {"tool": "route_ticket", "args": {"category": "BILL_HIGH"}, "result": "Routed to BILLING-OPS"}]}
```

In LangSmith, one `zia.handle_message` trace becomes a tree: model call → `check_tower` → model call →
`route_ticket` → final answer. Check which tools ran (and with what inputs), how many steps it took, and cost per
message. Offline, `ScriptedToolModel` stands in for the LLM and makes the same tool calls, so it's free and deterministic.

## Exercise (from the notebook)

1. **Q1** `no_signal_alert(dashboard, day_index)` — alert when `no_signal_share` falls >30% vs the day before, with `day`, `observed`, `baseline` and a ≥3-step `runbook`.
2. **Q2** `decisions_by_prompt(logs)` — count decisions per `prompt_version` per category.
3. **Q3** Roll `live_prompt` back to `v6` and show M01 is `NO_SIGNAL` again.

Reference solutions live in `zia_observability/alerts.py`; the CLI runs all three.

## Takeaways

- LangSmith tracing on from day one; **tags + metadata** (prompt version) on every call.
- Watch **behaviour** (category mix, re-contact, fallback rate, cost), not just latency and errors.
- Every alert: customer impact + the right baseline + a **runbook**.
- Redact PII **before** recording — once it's out, you can't put it back.
- Prompt changes go through the pipeline and canary like any other change.
