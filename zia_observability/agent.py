"""Agent mode: Zia checks the tower and routes the ticket with tools before answering.

``AgentClassifier`` wraps LangChain's ``create_agent`` and keeps the same
``classify(...) -> category`` interface, so the dashboard and alerts work unchanged.
Offline, ``ScriptedToolModel`` plays the LLM: it emits real tool calls
(check_tower → route_ticket → Label) and obeys the prompt literally, v7 bug included.
"""
import re
import uuid

from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy
from langchain.tools import tool
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from .classifier import PROMPTS, Label, offline_decision
from .world import TEAM_FOR, TOWER_FOR

DOWN_TOWERS = {"TWR-017": "DOWN since 18:55", "TWR-044": "DOWN since 08:40"}   # the week's two tower failures

AGENT_RULES = ("You have tools. First call check_tower with the customer's location, then call route_ticket "
               "with the category you chose, then give the final category.")


@tool
def check_tower(place: str) -> str:
    """Look up the status of the cell tower serving a place (e.g. 'Stadium', 'Queens')."""
    tower = TOWER_FOR.get(place)
    if tower is None:
        return f"No tower on record for {place!r}"
    return f"{tower}: {DOWN_TOWERS.get(tower, 'OK')}"


@tool
def route_ticket(category: str) -> str:
    """Send the ticket to the team that owns this complaint category."""
    team = TEAM_FOR.get(category)
    return f"Routed to {team}" if team else f"Unknown category {category!r}"


TOOLS = [check_tower, route_ticket]


def user_content(text: str, place: str | None) -> str:
    return f"Customer location: {place}\nMessage: {text}" if place else text


class ScriptedToolModel(BaseChatModel):
    """Offline chat model that walks the agent loop with real tool calls."""

    @property
    def _llm_type(self) -> str:
        return "zia-scripted-tool-model"

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult:
        system = next((m.content for m in messages if isinstance(m, SystemMessage)), "")
        human = next(m.content for m in messages if isinstance(m, HumanMessage))
        done = {m.name for m in messages if isinstance(m, ToolMessage)}
        match = re.match(r"Customer location: (.+)\nMessage: (.*)", human, re.S)
        place, text = (match.group(1), match.group(2)) if match else (None, human)
        category = offline_decision(system, text)

        if place and "check_tower" not in done:
            call = ("check_tower", {"place": place})
        elif "route_ticket" not in done:
            call = ("route_ticket", {"category": category})
        else:
            call = ("Label", {"category": category})
        message = AIMessage(content="", tool_calls=[{"name": call[0], "args": call[1],
                                                     "id": f"call_{uuid.uuid4().hex[:8]}", "type": "tool_call"}])
        return ChatResult(generations=[ChatGeneration(message=message)])


class AgentClassifier:
    def __init__(self, model=None):
        if model is None:
            from langchain_openai import ChatOpenAI
            model = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        self.agents = {v: create_agent(model, tools=TOOLS, system_prompt=f"{p} {AGENT_RULES}",
                                       response_format=ToolStrategy(Label), name=f"zia-agent-{v}")
                       for v, p in PROMPTS.items()}
        self.last_tools: list[dict] = []

    def classify(self, prompt_version: str, text: str, config: dict | None = None,
                 place: str | None = None) -> str:
        result = self.agents[prompt_version].invoke(
            {"messages": [{"role": "user", "content": user_content(text, place)}]}, config=config or {})
        outputs = {m.tool_call_id: m.content for m in result["messages"] if isinstance(m, ToolMessage)}
        self.last_tools = [{"tool": c["name"], "args": c["args"], "result": outputs.get(c["id"])}
                           for m in result["messages"] if isinstance(m, AIMessage)
                           for c in m.tool_calls if c["name"] != "Label"]
        return result["structured_response"].category
