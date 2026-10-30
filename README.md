# 🔭 Zia Went Quietly Wrong — Observability & Reliability demo

FDE Program · Phase 3 · Day 5. A runnable version of `notebooks/05_Observability_Reliability.ipynb`.

**The story:** someone adds one "helpful" line to Zia's system prompt (v7): *"If a message contains a number, it's
probably about money — classify it as BILL_HIGH."* For three days every machine dashboard is green, while
*"No signal at the stadium since 7pm"* is routed to billing. This project shows how logs, traces, behaviour metrics
and a single well-designed alert catch it on day one.

## In plain English

**The setup.** Zing Wireless is a made-up phone company. Its assistant, Zia, reads customer complaints and sorts
each one into one of five buckets — *no signal*, *bill too high*, *data plan*, *slow internet*, *SIM problem*. Each
bucket goes to a different team: no-signal complaints go to the network engineers, bill complaints go to billing.

**The bug.** Someone added one sentence to Zia's instructions: *"if a message has a number in it, it's about
money."* Now "No signal since **7pm**" goes to billing, and the customer is told to check their bill. Nothing
crashes and nothing slows down, so every "is the system up?" check stays green.

**What this project shows.** How you would have noticed on day one:

| Piece | Plain-English job |
|---|---|
| **Logbook** (`zia.py`) | One line per decision: a receipt number (trace id), which version of the instructions was used, the bucket chosen, how long it took. |
| **Two kinds of health check** (`dashboard.py`) | *"Is the machine OK?"* (speed, errors) and *"Is it doing the right thing?"* (what share of complaints land in "no signal"). The first stays perfect; the second falls from 35% to 0%. |
| **Smoke detector** (`alerts.py`) | Raises an alarm when the no-signal share drops sharply, and comes with a checklist (runbook) of what to do. |
| **Privacy filter** (`pii.py`) | Blacks out emails and card numbers before anything is sent to the AI or written to logs. |
| **Flight recorder** (LangSmith) | Records every AI call — the exact instructions it got, its answer, time and cost — so you can replay what happened. |

**The lesson in one line:** a system can be fast and error-free and still be wrong. Measure *what it decides*,
and always record *which instructions it was following*, so the cause is one search away.

### Old logic vs new logic (`--agent`)

| | **Old: a sorter with a rulebook** (default) | **New: a detective with a phone** (`--agent`) |
|---|---|---|
| How it works | Reads the message, checks its instructions, writes down a bucket. One question, one answer. | Reads the message, **picks up the phone** to check facts (`check_tower`) and take actions (`route_ticket`), then decides. |
| M01 with v7 | "Has a number → money" → **BILL_HIGH** | Checks the stadium tower → **"TWR-017: DOWN"** → still routes to billing → **BILL_HIGH** |
| What the log proves | Which instructions caused the wrong answer | Zia **had the right evidence and ignored it** |
| AI calls per message | 1 | 3 (tower → route → answer) |
| Best for | Pure sorting: cheap, fast, predictable | When Zia must look things up or act |

Both end with one of the five buckets, so the logbook, dashboard, alert and rollback work the same either way.

```
OLD  handle_message → OfflineClassifier / LLMClassifier.classify → one model call → bucket → log line
NEW  handle_message → AgentClassifier.classify → agent loop:
         model → check_tower("Stadium") → model → route_ticket(...) → model → final bucket
       → log line + "tools" (each tool, its inputs and its result)
```

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

## 🏋️ Hands-on exercise: Catch it on Tuesday

1. **Q1** `no_signal_alert(dashboard, day_index)` — alert when `no_signal_share` falls >30% vs the day before, with `day`, `observed`, `baseline` and a ≥3-step `runbook`.
2. **Q2** `decisions_by_prompt(logs)` — count decisions per `prompt_version` per category.
3. **Q3** Roll `live_prompt` back to `v6` and show M01 is `NO_SIGNAL` again.

| Part | Solution | Tests |
|---|---|---|
| Q1 | `zia_observability/alerts.py` → `no_signal_alert` | `test_alert_fires_on_tuesday_with_runbook`, `test_alert_quiet_when_nothing_changed` |
| Q2 | `zia_observability/alerts.py` → `decisions_by_prompt` | `test_decisions_by_prompt` |
| Q3 | CLI "Exercise Q3" section (`Zia.live_prompt = "v6"`) | `test_rollback_fixes_m01`, `test_cli_offline_end_to_end` |

The notebook's student cell (cell 19) intentionally keeps the `# TODO` stubs; cell 22 is the solution.

### Hands-on exercise demo

> **Demo offline, not live from the notebook.** The notebook's saved outputs show that real `gpt-4o-mini` did not
> fall for the v7 rule, so the alert printed `Tue → None` and the self-check failed — that kills the punchline in
> front of an audience. The offline classifier follows the prompt literally, so it reproduces every time, costs
> nothing and needs no API key.

**Setup (once, before the demo)**

```bash
cd observability
source .venv/bin/activate        # or: python -m venv .venv && source .venv/bin/activate && pip install -e '.[dev]'
```

#### Option A — one command (≈2 minutes)

```bash
python -m zia_observability
```

Scroll the output and point at four things:

1. **Demo 1** — the log line shows `"prompt_version": "v7", "category": "BILL_HIGH"` for *"No signal at the stadium
   since 7pm"*. 🗣️ *"The log already tells us which prompt caused it."*
2. **Dashboard** — latency ≈1.8s and errors 0 every day, but the no-signal share goes **0.35 → 0.00**.
   🗣️ *"The machine is green; the behaviour is broken."*
3. **Q1** — `Mon → None`, `Tue → {alert + runbook}`, `Wed → None`. 🗣️ *"It fires on Tuesday, the day of the change,
   with a checklist."*
4. **Q3** — `After the fix, M01 -> NO_SIGNAL`.

#### Option B — step by step (≈10 minutes, better for teaching)

Start `python` in the project folder and paste one block at a time, talking between them.

**Step 1 — the week's dashboards**

```python
from zia_observability import OfflineClassifier, Zia, simulate_days, no_signal_alert, decisions_by_prompt
from zia_observability.world import SAMPLE_MESSAGES

dashboard = simulate_days(OfflineClassifier())
for d in dashboard:
    print(d["day"], d["prompt"], "latency", d["p95_latency_s"], "errors", d["error_rate"], "no_signal", d["no_signal_share"])
```

```
Mon v6 latency 1.82 errors 0.0 no_signal 0.35
Tue v7 latency 1.81 errors 0.0 no_signal 0.0
Wed v7 latency 1.93 errors 0.0 no_signal 0.0
```

🗣️ *"If you only watched latency and errors, you'd say all is well. Look at the last column."*

**Step 2 (Q1) — the alert**

```python
for i in range(3):
    print(dashboard[i]["day"], "->", "ALERT" if no_signal_alert(dashboard, i) else "quiet")

no_signal_alert(dashboard, 1)        # show the full alert
```

```
Mon -> quiet
Tue -> ALERT
Wed -> quiet
```

🗣️ Point at `observed` vs `baseline`, the `impact` line and the 4-step `runbook`. *"A good alert says what's
wrong, compared with what, who's affected, and what to do."*

**Step 3 (Q2) — which prompt made which decisions**

```python
zia = Zia(OfflineClassifier(), live_prompt="v7", echo=False)
for m in SAMPLE_MESSAGES:
    zia.handle_message(m)
decisions_by_prompt(zia.logs)
```

```
{'v7': {'BILL_HIGH': 7, 'DATA_PLAN': 1, 'SLOW_INTERNET': 2, 'SIM_ISSUE': 2}}
```

🗣️ *"12 messages, 4 of them real outages — v7 put zero in NO_SIGNAL and 7 in BILL_HIGH, though only 2 are really
about bills. Because we log the prompt version, the cause is one search away."*

**Step 4 (Q3) — the fix**

```python
zia.live_prompt = "v6"
zia.handle_message(SAMPLE_MESSAGES[0])
```

```
'NO_SIGNAL'
```

🗣️ *"Roll back the prompt, and the stadium customer goes to network ops again."*

**Step 5 (optional) — the self-check**

```bash
pytest -v -k "alert or decisions or rollback"
```

Green ticks for "fires on Tuesday", "quiet when nothing changed", "counts per prompt" and "rollback" — the repo's
version of the notebook's `check_day5()`.

#### Optional extras

- **Agent version** — `python -m zia_observability --agent`. The log shows the tower check found
  `TWR-017: DOWN`, yet the ticket still went to billing.
- **LangSmith** — `python -m zia_observability --live` with your keys, then filter by metadata
  `prompt_version = v7`. Warn the audience that the real model may *not* misroute the message — that's a lesson too.
- **Closing line** — *"Wednesday says 'quiet', yet Zia is still broken. Comparing with yesterday only catches the
  moment of change."* This sets up a follow-on exercise: compare against the last known-good baseline so the alert
  keeps firing until the fix lands.

#### Testing with your own message

```bash
python -c "
from zia_observability import Zia, OfflineClassifier
zia = Zia(OfflineClassifier(), live_prompt='v7')
msg = {'id': 'X1', 'place': 'Brooklyn', 'text': 'My phone has no signal in Brooklyn since 6am'}
zia.handle_message(msg)        # bad prompt  -> BILL_HIGH
zia.live_prompt = 'v6'
zia.handle_message(msg)        # good prompt -> NO_SIGNAL
"
```

The offline classifier only knows keywords ("signal", "bill", "slow", "SIM", "plan"…); use `LLMClassifier()` or
`AgentClassifier()` with your API key for real judgement.

## Takeaways

- LangSmith tracing on from day one; **tags + metadata** (prompt version) on every call.
- Watch **behaviour** (category mix, re-contact, fallback rate, cost), not just latency and errors.
- Every alert: customer impact + the right baseline + a **runbook**.
- Redact PII **before** recording — once it's out, you can't put it back.
- Prompt changes go through the pipeline and canary like any other change.
