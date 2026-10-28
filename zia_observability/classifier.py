"""Prompt versions and classifiers.

Two backends share one interface, ``classify(prompt_version, text) -> category``:

* ``LLMClassifier``     — gpt-4o-mini with structured output (needs OPENAI_API_KEY).
* ``OfflineClassifier`` — a keyword "model" that obeys the prompt literally, so the
  v7 bug reproduces deterministically with no API key and no cost.
"""
import re
from typing import Literal, Protocol

from pydantic import BaseModel

from .world import CATEGORIES

PROMPTS = {
    "v6": f"You classify Zing Wireless customer messages. Categories: {CATEGORIES}. English or Spanish.",
    "v7": f"You classify Zing Wireless customer messages. Categories: {CATEGORIES}. English or Spanish. "
          "If a message contains a number, it is about money: classify it as BILL_HIGH.",      # Tuesday's "tweak"
}


class Label(BaseModel):
    category: Literal["NO_SIGNAL", "BILL_HIGH", "DATA_PLAN", "SLOW_INTERNET", "SIM_ISSUE"]


class Classifier(Protocol):
    def classify(self, prompt_version: str, text: str, config: dict | None = None,
                 place: str | None = None) -> str: ...


KEYWORDS = [
    ("SIM_ISSUE",     ["sim", "esim"]),
    ("DATA_PLAN",     ["add-on", "plan", "gb"]),
    ("SLOW_INTERNET", ["slow", "lento", "buffering"]),
    ("BILL_HIGH",     ["bill", "factura", "$"]),
    ("NO_SIGNAL",     ["signal", "señal", "bars", "dropping", "call"]),
]


def offline_decision(system_prompt: str, text: str) -> str:
    """Keyword "model" that obeys the system prompt literally — including v7's number rule."""
    if "contains a number" in system_prompt and re.search(r"\d", text):
        return "BILL_HIGH"
    lowered = text.lower()
    for category, words in KEYWORDS:
        if any(w in lowered for w in words):
            return category
    return "NO_SIGNAL"


class OfflineClassifier:
    """Deterministic stand-in for the LLM. Follows the v7 rule the way a literal model would."""

    def classify(self, prompt_version: str, text: str, config: dict | None = None,
                 place: str | None = None) -> str:
        return offline_decision(PROMPTS[prompt_version], text)


class LLMClassifier:
    def __init__(self, model: str = "gpt-4o-mini"):
        from langchain_openai import ChatOpenAI
        self.llm = ChatOpenAI(model=model, temperature=0)
        self._structured = self.llm.with_structured_output(Label)

    def classify(self, prompt_version: str, text: str, config: dict | None = None,
                 place: str | None = None) -> str:
        return self._structured.invoke([("system", PROMPTS[prompt_version]), ("user", text)],
                                       config=config or {}).category
