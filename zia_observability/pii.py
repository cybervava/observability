"""Redact personal data before it reaches the model, logs or traces.

``build_safe_zia`` uses LangChain's built-in ``PIIMiddleware`` (needs an LLM).
``redact`` is a small offline equivalent used by the CLI demo and the tests.
"""
import re

EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
CARD = re.compile(r"\b(?:\d[ -]?){12,15}(\d{4})\b")


def redact(text: str) -> str:
    text = EMAIL.sub("[REDACTED_EMAIL]", text)
    return CARD.sub(lambda m: "****-****-****-" + m.group(1), text)


def build_safe_zia(llm):
    from langchain.agents import create_agent
    from langchain.agents.middleware import PIIMiddleware

    return create_agent(
        llm, tools=[],
        system_prompt="You are Zia from Zing Wireless. Reply in one short sentence.",
        middleware=[PIIMiddleware("email", strategy="redact"), PIIMiddleware("credit_card", strategy="mask")],
    )
