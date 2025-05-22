"""Rapid prototype using Agents SDK and LiveTranscriber."""

from __future__ import annotations

import importlib
import json
import logging
import os
from pathlib import Path
from typing import Any, Callable

from agents import function_tool
from livetranscriber import LiveTranscriber

from . import catalog as catalog_module

logger = logging.getLogger(__name__)

MEMORY_PATH = Path(__file__).with_name("memory.json")
TRANSCRIBER_REF: dict[str, LiveTranscriber | None] = {"instance": None}


def load_memory() -> dict[str, Any]:
    """Load persisted memory from disk."""

    if MEMORY_PATH.exists():
        return json.loads(MEMORY_PATH.read_text())
    return {}


def save_memory(data: dict[str, Any]) -> None:
    """Persist memory to disk."""

    MEMORY_PATH.write_text(json.dumps(data))


def reload_catalog() -> None:
    """Reload the catalog module."""

    importlib.reload(catalog_module)


def call_function(func: Callable[..., Any]) -> Any:
    """Call a function and return its result."""

    return func()


def plan_actions(command: str) -> list[str]:
    """Determine which catalog functions to call."""

    mapping = {"open google chrome": ["open_chrome"]}
    return mapping.get(command.lower(), [])


@function_tool
def list_functions() -> list[str]:
    """List available functions in the catalog."""

    return [n for n in dir(catalog_module.Catalog) if not n.startswith("_")]


def ensure_functions(functions: list[str]) -> None:
    """Create missing functions in the catalog."""

    existing = set(list_functions())
    missing = [f for f in functions if f not in existing]
    if not missing:
        return

    for name in missing:
        with open(catalog_module.__file__, "a", encoding="utf-8") as fp:
            fp.write(f"\n    def {name}(self):\n        pass\n")

    reload_catalog()


def execute_sequence(functions: list[str]) -> None:
    """Execute a list of catalog functions in order."""

    cat = catalog_module.Catalog()
    for name in functions:
        func = getattr(cat, name)
        call_function(func)


def manager(utterance: str, transcriber: LiveTranscriber | None = None) -> None:
    """Entry point for new utterances from the transcriber."""

    logger.info("User said: %s", utterance)
    functions = plan_actions(utterance)
    ensure_functions(functions)
    if len(functions) > 1:
        new_func = "run_" + "_".join(functions)
        ensure_functions([new_func])
        with open(catalog_module.__file__, "a", encoding="utf-8") as fp:
            fp.write(f"\n    def {new_func}(self):\n")
            for name in functions:
                fp.write(f"        self.{name}()\n")
        reload_catalog()
        data = load_memory()
        data["pending"] = new_func
        save_memory(data)
        os.execv(os.sys.executable, [os.sys.executable, __file__])
    elif functions:
        execute_sequence(functions)


def resume_pending() -> None:
    """Run any pending function after reload."""

    data = load_memory()
    pending = data.pop("pending", None)
    if pending:
        save_memory(data)
        execute_sequence([pending])


def _run_transcriber() -> None:
    """Run the LiveTranscriber."""

    logger.debug("Starting LiveTranscriber...")
    tr = LiveTranscriber(callback=manager)
    TRANSCRIBER_REF["instance"] = tr
    tr.run()
    logger.debug("LiveTranscriber stopped")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    resume_pending()
    _run_transcriber()
