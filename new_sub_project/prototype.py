"""Prototype voice assistant using Agents SDK and LiveTranscriber."""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

from livetranscriber import LiveTranscriber

from . import catalog

CATALOG_PATH = Path(__file__).with_name("catalog.py")
STATE_PATH = Path(__file__).with_name("state.json")

transcriber_reference: dict[str, LiveTranscriber | None] = {"instance": None}


def load_state() -> dict[str, Any]:
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text())
    return {}


def save_state(data: dict[str, Any]) -> None:
    STATE_PATH.write_text(json.dumps(data))


def reload_self() -> None:
    """Reload the current Python process."""
    python = sys.executable
    os.execv(python, [python] + sys.argv)


def function_exists(name: str) -> bool:
    return hasattr(catalog.Catalog, name)


def append_to_catalog(code: str) -> None:
    with open(CATALOG_PATH, "a", encoding="utf-8") as fp:
        fp.write(f"\n{code}\n")


async def plan_functions(utterance: str) -> dict[str, Any]:
    """Use an agent to plan required functions.

    This is a stub implementation that returns a minimal plan.
    """
    # In a real implementation we would call an Agent from the SDK
    # to understand the utterance and produce a plan.
    return {
        "missing_functions": {
            "say_hello": "def say_hello():\n    print(\"Hello\")"
        },
        "sequence": ["say_hello"],
        "composite_name": "run_task",
    }


def create_composite_function(name: str, sequence: list[str]) -> str:
    body_lines = [f"        catalog.Catalog.{fn}()" for fn in sequence]
    body = "\n".join(body_lines) if body_lines else "        pass"
    return f"def {name}():\n{body}\n"


def handle_plan(plan: dict[str, Any]) -> None:
    missing = plan.get("missing_functions", {})
    for fname, code in missing.items():
        if not function_exists(fname):
            append_to_catalog(f"    {code}")
    composite = create_composite_function(plan["composite_name"], plan["sequence"])
    append_to_catalog(f"    {composite}")
    save_state({"call": plan["composite_name"]})
    reload_self()


def process_utterance(utterance: str) -> None:
    if not utterance.strip():
        return
    state = load_state()
    if state:
        func = getattr(catalog.Catalog, state["call"], None)
        if callable(func):
            func()
        STATE_PATH.unlink(missing_ok=True)
        return
    plan = {
        "missing_functions": {},
        "sequence": [],
        "composite_name": "",
    }
    # Placeholder: call plan_functions to simulate planning
    plan = asyncio.run(plan_functions(utterance))  # type: ignore[var-annotated]
    handle_plan(plan)


async def manager(utterance: str, transcriber: LiveTranscriber | None = None) -> None:
    process_utterance(utterance)


def _run_transcriber() -> None:
    tr = LiveTranscriber(callback=manager)
    transcriber_reference["instance"] = tr
    tr.run()


if __name__ == "__main__":
    _run_transcriber()
