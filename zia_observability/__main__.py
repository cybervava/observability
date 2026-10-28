"""Run the Day 5 demo end to end: `python -m zia_observability [--live]`."""
import argparse
import os

from .alerts import decisions_by_prompt, no_signal_alert
from .classifier import LLMClassifier, OfflineClassifier
from .dashboard import plot_dashboard, simulate_days
from .pii import redact
from .world import SAMPLE_MESSAGES


def setup_tracing():
    from dotenv import load_dotenv
    load_dotenv()
    os.environ.setdefault("LANGSMITH_PROJECT", "zia-day-5")
    if os.getenv("LANGSMITH_API_KEY"):
        os.environ["LANGSMITH_TRACING"] = "true"
        print("LangSmith tracing is ON  -> https://smith.langchain.com")
    else:
        print("LangSmith is off (add LANGSMITH_API_KEY to .env to see traces)")


def build_classifier(live: bool, agent: bool):
    if agent:
        from .agent import AgentClassifier, ScriptedToolModel
        return AgentClassifier() if live else AgentClassifier(ScriptedToolModel())
    return LLMClassifier() if live else OfflineClassifier()


def section(title: str):
    print(f"\n=== {title} ===")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="use gpt-4o-mini instead of the offline classifier")
    parser.add_argument("--agent", action="store_true",
                        help="use a LangChain agent that checks the tower and routes the ticket with tools")
    parser.add_argument("--plot", default="dashboard.png", help="where to save the dashboard chart")
    args = parser.parse_args()

    setup_tracing()
    classifier = build_classifier(args.live, args.agent)
    print("Classifier:", type(classifier).__name__)

    from .zia import Zia
    section("Demo 1 — trace one message with Tuesday's prompt (v7)")
    zia = Zia(classifier, live_prompt="v7")
    zia.handle_message(SAMPLE_MESSAGES[0])

    section("Demo 2 — redact personal data before anything is recorded")
    raw = "No signal again! I'm jane.doe@gmail.com and my card is 4111-1111-1111-1111, refund me"
    print("What the model (and the trace) sees:", redact(raw))

    section("Demo 2 — three days of dashboards")
    dashboard = simulate_days(classifier)
    for row in dashboard:
        print(row)
    print("Chart saved to", plot_dashboard(dashboard, args.plot))

    section("Exercise Q1 — the alert that would have caught it on Tuesday")
    for i, row in enumerate(dashboard):
        print(row["day"], "->", no_signal_alert(dashboard, i))

    section("Exercise Q2 — decisions by prompt version")
    zia.echo = False
    for m in SAMPLE_MESSAGES:
        zia.handle_message(m)
    print(decisions_by_prompt(zia.logs))

    section("Exercise Q3 — roll back to v6")
    zia.live_prompt = "v6"
    print("After the fix, M01 ->", zia.handle_message(SAMPLE_MESSAGES[0]))


if __name__ == "__main__":
    main()
