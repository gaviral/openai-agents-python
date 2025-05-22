from __future__ import annotations

import argparse
import json
import logging
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, List

from agents import Agent, FunctionTool, Runner, set_tracing_disabled
from livetranscriber import LiveTranscriber

from .catalog import Catalog

logger = logging.getLogger(__name__)
STATE_PATH = Path.home() / ".meta_agent" / "state.json"

transcriber_reference: dict[str, LiveTranscriber] = {}


# ----------------------- State persistence -----------------------


def load_state() -> dict[str, Any]:
    if not STATE_PATH.exists():
        STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        data = {"pending_tasks": [], "long_running_context": {}}
        STATE_PATH.write_text(json.dumps(data))
        return data
    return json.loads(STATE_PATH.read_text())


def save_state(data: dict[str, Any]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(data))


# ----------------------- Catalog helpers -----------------------


def catalog_tools() -> List[FunctionTool]:
    tools = []
    for value in Catalog.__dict__.values():
        if isinstance(value, FunctionTool):
            tools.append(value)
    return tools


def has_helper(name: str) -> bool:
    return any(tool.name == name for tool in catalog_tools())


def append_open_helper(app_name: str) -> None:
    file_path = Path(__file__).with_name("catalog.py")
    src = file_path.read_text().splitlines()
    if "pass" in src:
        src.remove("    pass")
    helper_name = f"open_{app_name.lower().replace(' ', '_')}"
    if any(f"def {helper_name}" in line for line in src):
        return
    lines = [
        "",
        "    @staticmethod",
        "    @function_tool",
        f"    def {helper_name}() -> str:",
        f'        "Open {app_name}."',
        f'        return Catalog._osascript_activate("{app_name}")',
    ]
    if "_osascript_activate" not in "\n".join(src):
        helper = [
            "",
            "    @staticmethod",
            "    def _osascript_activate(app: str) -> str:",
            "        subprocess.run(['osascript', '-e', f'tell application \"{app}\" to activate'], check=True)",
            "        return f'{app} activated'",
        ]
        src.extend(helper)
    src.extend(lines)
    file_path.write_text("\n".join(src))
    try:
        subprocess.run(["black", str(file_path)], check=False)
    except Exception:
        pass


# ----------------------- Agent runner -----------------------


def run_agent(utterance: str, model: str) -> None:
    agent = Agent(
        name="Assistant",
        instructions="You are a helpful assistant.",
        tools=catalog_tools(),
        model=model,
    )
    result = Runner.run_sync(agent, utterance)
    print(result.final_output)


# ----------------------- Manager -----------------------


def manager(utterance: str, transcriber: LiveTranscriber | None = None) -> None:
    print(f"User said: {utterance}")
    match = re.match(r"open (.+)", utterance, re.IGNORECASE)
    if match:
        app = match.group(1).strip()
        func_name = f"open_{app.lower().replace(' ', '_')}"
        if not has_helper(func_name):
            append_open_helper(app)
            state = load_state()
            state.setdefault("pending_tasks", []).append(utterance)
            save_state(state)
            subprocess.Popen([sys.executable, "main.py", *sys.argv[1:]])
            time.sleep(2)
            sys.exit(0)
    run_agent(utterance, os.getenv("META_AGENT_MODEL", "o3-mini"))


# ----------------------- Transcriber thread -----------------------


def _run_transcriber() -> None:
    transcriber = LiveTranscriber(callback=manager)
    transcriber_reference["main"] = transcriber
    thread = threading.Thread(target=transcriber.run, daemon=True)
    thread.start()
    thread.join()


# ----------------------- Main CLI -----------------------


def main(argv: List[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=os.getenv("META_AGENT_MODEL", "o3-mini"))
    parser.add_argument("--no-trace", action="store_true")
    args = parser.parse_args(argv)
    if args.no_trace:
        set_tracing_disabled(True)
    state = load_state()
    tasks = state.get("pending_tasks", [])
    if tasks:
        state["pending_tasks"] = []
        save_state(state)
        for task in tasks:
            manager(task)
    else:
        _run_transcriber()


if __name__ == "__main__":
    main()
