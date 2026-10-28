"""Behaviour alerts with runbooks, and log analysis by prompt version."""
from collections import Counter

DROP_THRESHOLD = 0.7   # alert when today's share is more than 30% below yesterday's

RUNBOOK = [
    "1. Check what changed in the last 24h — code, model AND prompts",
    "2. In LangSmith, filter NO_SIGNAL-looking messages by prompt_version",
    "3. If a prompt change caused it, switch back to the last good version",
    "4. Post in #zia-incidents and schedule a blameless review",
]


def no_signal_alert(dashboard: list[dict], day_index: int) -> dict | None:
    if day_index == 0:
        return None
    today, yesterday = dashboard[day_index], dashboard[day_index - 1]
    if today["no_signal_share"] < yesterday["no_signal_share"] * DROP_THRESHOLD:
        return {"day": today["day"], "observed": today["no_signal_share"], "baseline": yesterday["no_signal_share"],
                "prompt": today.get("prompt"),
                "impact": "customers with no signal are getting the wrong reply",
                "runbook": list(RUNBOOK)}
    return None


def decisions_by_prompt(logs: list[dict]) -> dict[str, dict[str, int]]:
    counts: dict[str, Counter] = {}
    for line in logs:
        counts.setdefault(line["prompt_version"], Counter())[line["category"]] += 1
    return {version: dict(c) for version, c in counts.items()}
