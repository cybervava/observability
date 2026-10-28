"""Three days of dashboards: green machine signals, broken behaviour signals."""
import random

from .classifier import PROMPTS, Classifier
from .world import SAMPLE_MESSAGES

DAYS = {"Mon": "v6", "Tue": "v7", "Wed": "v7"}


def simulate_days(classifier: Classifier, days: dict = DAYS, per_day: int = 300, seed: int = 5) -> list[dict]:
    """Ask each prompt version about each sample once, then replay those answers for `per_day` messages."""
    rng = random.Random(seed)
    answers = {v: {m["text"]: classifier.classify(v, m["text"]) for m in SAMPLE_MESSAGES} for v in PROMPTS}

    dashboard = []
    for day, version in days.items():
        msgs = [rng.choice(SAMPLE_MESSAGES) for _ in range(per_day)]
        chosen = [answers[version][m["text"]] for m in msgs]
        dashboard.append({
            "day": day, "prompt": version,
            "p95_latency_s": round(rng.uniform(1.8, 2.1), 2),                    # machine signals: all normal
            "error_rate": 0.0,
            "no_signal_share": round(chosen.count("NO_SIGNAL") / len(chosen), 2),  # behaviour signal
            "bill_share": round(chosen.count("BILL_HIGH") / len(chosen), 2),
        })
    return dashboard


def plot_dashboard(dashboard: list[dict], path: str = "dashboard.png") -> str:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    days = [d["day"] for d in dashboard]
    fig, ax = plt.subplots(1, 2, figsize=(11, 3.2))
    ax[0].bar(days, [d["p95_latency_s"] for d in dashboard], color="seagreen")
    ax[0].set_title("P95 latency (s) - looks fine")
    ax[1].plot(days, [d["no_signal_share"] for d in dashboard], "o-", label="NO_SIGNAL share")
    ax[1].plot(days, [d["bill_share"] for d in dashboard], "o-", label="BILL_HIGH share")
    ax[1].set_title("Category mix - the real story")
    ax[1].legend()
    plt.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return path
