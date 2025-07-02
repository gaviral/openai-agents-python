"""Simple prototype for meta-agent system."""

import asyncio
import json
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any, Optional

from livetranscriber import LiveTranscriber
from agents import Agent, Runner, function_tool

from .catalog import Catalog

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# State file for persistence
STATE_PATH = Path(__file__).parent / "state.json"

# Keep reference to transcriber
transcriber_reference = {"instance": None}


def load_state() -> Dict[str, Any]:
    """Load state from disk."""
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text())
    return {}


def save_state(data: Dict[str, Any]) -> None:
    """Save state to disk."""
    STATE_PATH.write_text(json.dumps(data))


def reload_self() -> None:
    """Reload the current process."""
    logger.info("Reloading process...")
    python = sys.executable
    os.execv(python, [python] + sys.argv)


def function_exists(name: str) -> bool:
    """Check if a function exists in the Catalog."""
    return hasattr(Catalog, name) and callable(getattr(Catalog, name))


def append_to_catalog(code: str) -> None:
    """Add code to the catalog file."""
    catalog_path = Path(__file__).parent / "catalog.py"
    with open(catalog_path, "a", encoding="utf-8") as fp:
        fp.write(f"\n{code}\n")


@function_tool
def open_chrome() -> str:
    """Open Google Chrome browser."""
    try:
        subprocess.run(["open", "-a", "Google Chrome"], check=True)
        return "Chrome opened successfully"
    except subprocess.SubprocessError:
        return "Failed to open Chrome"


@function_tool
def create_text_file(filename: str, content: str = "") -> str:
    """Create a text file with optional content."""
    try:
        path = Path.home() / filename
        with open(path, "w") as f:
            f.write(content)
        return f"Created file at {path}"
    except Exception as e:
        return f"Error creating file: {e}"


async def process_command(utterance: str) -> None:
    """Process a user command."""
    logger.info(f"Processing command: {utterance}")
    
    # Check if we have a pending task
    state = load_state()
    if state:
        func_name = state.get("call")
        if func_name and function_exists(func_name):
            logger.info(f"Executing function: {func_name}")
            func = getattr(Catalog, func_name)
            func()
        # Clear state
        STATE_PATH.unlink(missing_ok=True)
        return
    
    # For this simple prototype, just handle a few hardcoded commands
    if "chrome" in utterance.lower() or "browser" in utterance.lower():
        code = """    @staticmethod
    def open_chrome() -> str:
        \"\"\"Open Google Chrome browser.\"\"\"
        subprocess.run(["open", "-a", "Google Chrome"], check=True)
        return "Chrome opened successfully"
"""
        append_to_catalog(code)
        save_state({"call": "open_chrome"})
        reload_self()
    
    elif "text file" in utterance.lower() or "create file" in utterance.lower():
        code = """    @staticmethod
    def create_text_file() -> str:
        \"\"\"Create a new text file on the desktop.\"\"\"
        path = Path.home() / "Desktop" / "new_file.txt"
        with open(path, "w") as f:
            f.write("Created by meta-agent")
        return f"Created file at {path}"
"""
        append_to_catalog(code)
        save_state({"call": "create_text_file"})
        reload_self()
    
    else:
        logger.info("Command not recognized")


async def manager(utterance: str, transcriber: Optional[LiveTranscriber] = None) -> None:
    """Entry point for new utterances."""
    logger.info(f"User said: {utterance}")
    await process_command(utterance)


def _run_transcriber() -> None:
    """Run the LiveTranscriber."""
    logger.info("Starting LiveTranscriber...")
    tr = LiveTranscriber(callback=manager)
    transcriber_reference["instance"] = tr
    tr.run()
    logger.info("LiveTranscriber stopped")


if __name__ == "__main__":
    _run_transcriber() 