import sys

from zia_observability import Zia, no_signal_alert, simulate_days
from zia_observability.agent import AgentClassifier, ScriptedToolModel, check_tower, route_ticket
from zia_observability.world import SAMPLE_MESSAGES


def offline_agent():
    return AgentClassifier(ScriptedToolModel())


def test_check_tower_reports_down_ok_and_unknown():
    assert check_tower.invoke({"place": "Stadium"}) == "TWR-017: DOWN since 18:55"
    assert check_tower.invoke({"place": "Brooklyn"}) == "TWR-031: OK"
    assert "No tower" in check_tower.invoke({"place": "Mars"})


def test_route_ticket_uses_team_table():
    assert route_ticket.invoke({"category": "NO_SIGNAL"}) == "Routed to NETWORK-OPS"
    assert "Unknown category" in route_ticket.invoke({"category": "LOST_PHONE"})


def test_agent_v6_checks_tower_then_routes_to_network():
    agent = offline_agent()
    assert agent.classify("v6", SAMPLE_MESSAGES[0]["text"], place="Stadium") == "NO_SIGNAL"
    assert [t["tool"] for t in agent.last_tools] == ["check_tower", "route_ticket"]
    assert agent.last_tools[1]["result"] == "Routed to NETWORK-OPS"


def test_agent_v7_ignores_tower_evidence():
    agent = offline_agent()
    assert agent.classify("v7", SAMPLE_MESSAGES[0]["text"], place="Stadium") == "BILL_HIGH"
    tower, route = agent.last_tools
    assert "DOWN" in tower["result"] and route["result"] == "Routed to BILLING-OPS"


def test_agent_without_place_skips_tower_check():
    agent = offline_agent()
    assert agent.classify("v6", "My new eSIM won't activate") == "SIM_ISSUE"
    assert [t["tool"] for t in agent.last_tools] == ["route_ticket"]


def test_zia_logs_tool_calls_in_agent_mode():
    zia = Zia(offline_agent(), live_prompt="v7", echo=False)
    zia.handle_message(SAMPLE_MESSAGES[0])
    assert [t["tool"] for t in zia.logs[0]["tools"]] == ["check_tower", "route_ticket"]


def test_agent_dashboard_alert_fires_on_tuesday():
    dashboard = simulate_days(offline_agent())
    assert no_signal_alert(dashboard, 1) and no_signal_alert(dashboard, 2) is None


def test_cli_agent_mode(tmp_path, monkeypatch, capsys):
    from zia_observability.__main__ import main
    monkeypatch.delenv("LANGSMITH_API_KEY", raising=False)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["zia", "--agent", "--plot", str(tmp_path / "d.png")])
    main()
    out = capsys.readouterr().out
    assert "Classifier: AgentClassifier" in out and '"tool": "check_tower"' in out
    assert "After the fix, M01 -> NO_SIGNAL" in out
