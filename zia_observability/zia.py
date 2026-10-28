"""Zia's message handler: one structured JSON log line per decision, with a trace id."""
import json
import time
import uuid

from langsmith import traceable

from .classifier import Classifier


class Zia:
    def __init__(self, classifier: Classifier, live_prompt: str = "v7", echo: bool = True):
        self.classifier = classifier
        self.live_prompt = live_prompt
        self.echo = echo
        self.logs: list[dict] = []

    def log(self, **fields):
        self.logs.append(fields)
        if self.echo:
            print(json.dumps(fields))

    @traceable(name="zia.handle_message")
    def handle_message(self, message: dict) -> str:
        trace_id = uuid.uuid4().hex[:8]
        start = time.perf_counter()
        config = {"tags": ["zia", self.live_prompt],
                  "metadata": {"prompt_version": self.live_prompt, "message_id": message["id"]}}
        category = self.classifier.classify(self.live_prompt, message["text"], config=config)
        self.log(trace_id=trace_id, message_id=message["id"], step="classify", prompt_version=self.live_prompt,
                 category=category, ms=round((time.perf_counter() - start) * 1000))
        return category
