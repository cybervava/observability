from zia_observability import OfflineClassifier, Zia, decisions_by_prompt, no_signal_alert, simulate_days
from zia_observability.pii import redact
from zia_observability.world import SAMPLE_MESSAGES


def test_offline_v6_matches_labels():
    clf = OfflineClassifier()
    assert all(clf.classify("v6", m["text"]) == m["label"] for m in SAMPLE_MESSAGES)


def test_offline_v7_reproduces_the_bug():
    assert OfflineClassifier().classify("v7", "No signal at the stadium since 7pm!!") == "BILL_HIGH"


def test_log_line_has_trace_id_and_prompt_version():
    zia = Zia(OfflineClassifier(), live_prompt="v7", echo=False)
    zia.handle_message(SAMPLE_MESSAGES[0])
    line = zia.logs[0]
    assert len(line["trace_id"]) == 8
    assert line["prompt_version"] == "v7" and line["category"] == "BILL_HIGH"


def test_alert_fires_on_tuesday_with_runbook():
    dashboard = simulate_days(OfflineClassifier())
    tue = no_signal_alert(dashboard, 1)
    assert tue and tue["day"] == "Tue" and tue["prompt"] == "v7"
    assert tue["observed"] < tue["baseline"] and len(tue["runbook"]) >= 3


def test_alert_quiet_when_nothing_changed():
    dashboard = simulate_days(OfflineClassifier())
    assert no_signal_alert(dashboard, 0) is None
    assert no_signal_alert(dashboard, 2) is None


def test_machine_signals_stay_green():
    dashboard = simulate_days(OfflineClassifier())
    assert all(d["error_rate"] == 0.0 and d["p95_latency_s"] < 2.2 for d in dashboard)


def test_decisions_by_prompt():
    logs = [{"prompt_version": "v7", "category": "BILL_HIGH"},
            {"prompt_version": "v7", "category": "BILL_HIGH"},
            {"prompt_version": "v6", "category": "NO_SIGNAL"}]
    assert decisions_by_prompt(logs) == {"v7": {"BILL_HIGH": 2}, "v6": {"NO_SIGNAL": 1}}


def test_rollback_fixes_m01():
    zia = Zia(OfflineClassifier(), live_prompt="v6", echo=False)
    assert zia.handle_message(SAMPLE_MESSAGES[0]) == "NO_SIGNAL"


def test_redact_email_and_card():
    out = redact("I'm jane.doe@gmail.com and my card is 4111-1111-1111-1111")
    assert "jane.doe" not in out and "[REDACTED_EMAIL]" in out
    assert "****-****-****-1111" in out and "4111-1111-1111-1111" not in out


def test_cli_offline_end_to_end(tmp_path, monkeypatch, capsys):
    import sys
    from zia_observability.__main__ import main
    monkeypatch.delenv("LANGSMITH_API_KEY", raising=False)
    monkeypatch.chdir(tmp_path)
    chart = tmp_path / "dash.png"
    monkeypatch.setattr(sys, "argv", ["zia", "--plot", str(chart)])
    main()
    out = capsys.readouterr().out
    assert chart.exists()
    assert "Tue -> {'day': 'Tue'" in out
    assert "After the fix, M01 -> NO_SIGNAL" in out
