"""
Meta-agent prototype that dynamically extends a catalog of functions based on user commands.
Uses OpenAI Agents SDK and LiveTranscriber for voice input.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from agents import Agent, Runner, function_tool
from livetranscriber import LiveTranscriber

from .catalog import Catalog
from .function_parser import parse_plan_from_agent_response

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# State file to remember tasks between reloads
STATE_PATH = Path(__file__).parent / "state.json"

# Keep reference to transcriber to prevent garbage collection
transcriber_reference: Dict[str, Optional[LiveTranscriber]] = {"instance": None}


def load_state() -> Dict[str, Any]:
    """Load the current state from disk."""
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text())
    return {}


def save_state(data: Dict[str, Any]) -> None:
    """Save the current state to disk."""
    STATE_PATH.write_text(json.dumps(data))


def reload_self() -> None:
    """Reload the current Python process."""
    logger.info("Reloading process...")
    python = sys.executable
    os.execv(python, [python] + sys.argv)


def print_utterance(utterance: str) -> None:
    """Print the user's utterance."""
    logger.info(f"User said: {utterance}")


def function_exists(name: str) -> bool:
    """Check if a function exists in the catalog."""
    return hasattr(Catalog, name) and callable(getattr(Catalog, name))


def append_to_catalog(code: str) -> None:
    """Append code to the catalog.py file."""
    catalog_path = Path(__file__).parent / "catalog.py"
    with open(catalog_path, "a", encoding="utf-8") as fp:
        fp.write(f"\n{code}\n")


@function_tool
def get_available_functions() -> str:
    """Get a list of all available functions in the Catalog."""
    function_names = [name for name, func in Catalog.__dict__.items() 
                    if callable(func) and not name.startswith('_')]
    
    if not function_names:
        return "No functions are currently available in the Catalog."
    
    return "Available functions: " + ", ".join(function_names)


async def generate_plan(utterance: str) -> Dict[str, Any]:
    """
    Use an agent to generate a plan for implementing the user's command.
    
    The plan consists of:
    - missing_functions: Dict of function_name -> function_code for functions that need to be created
    - sequence: List of function names to call in sequence
    - composite_name: Name for a new function that will call the sequence
    """
    planning_agent = Agent(
        name="Function Planner",
        instructions="""
        You are an expert function planner for a MacOS system. Your job is to:
        
        1. Analyze what the user wants to do on their MacOS system
        2. Check which functions already exist in the Catalog
        3. Determine what new functions need to be created 
        4. Define the sequence of function calls needed to fulfill the request
        
        All functions MUST follow Single Responsibility Principle strictly. Make them as small and focused 
        as possible, often just one line. Functions can and should call other functions when appropriate.
        
        All functions must be methods of the Catalog class.
        
        When providing your response, include:
        1. Any new functions needed, written as complete Python code blocks in ```python format
        2. A clear statement of which functions to call in sequence
        3. A suggested name for a composite function if multiple functions need to be called
        
        Example function format:
        ```python
        def open_chrome():
            """Open Google Chrome browser."""
            subprocess.run(["open", "-a", "Google Chrome"], check=True)
            return "Chrome opened successfully"
        ```
        
        Ensure each function has:
        - Proper docstring
        - Appropriate return values
        - Error handling where necessary
        - Minimal implementation that follows SRP
        """,
        tools=[get_available_functions],
    )
    
    # Run the planning agent with the user's utterance
    result = await Runner.run(planning_agent, f"Plan how to implement this command: '{utterance}'")
    
    # Parse the response to extract the plan
    functions, sequence, composite_name = parse_plan_from_agent_response(result.final_output)
    
    # If we couldn't extract any functions or sequence, use a fallback
    if not functions and not sequence:
        logger.warning("Could not extract functions or sequence from response, using fallback")
        function_name = "dummy_function"
        if "open" in utterance.lower() and "chrome" in utterance.lower():
            function_name = "open_chrome"
            code = """    @staticmethod
    def open_chrome() -> str:
        \"\"\"Open Google Chrome browser.\"\"\"
        subprocess.run(["open", "-a", "Google Chrome"], check=True)
        return "Chrome opened successfully"
"""
            functions = {function_name: code}
        else:
            code = f"""    @staticmethod
    def dummy_function() -> str:
        \"\"\"Placeholder function.\"\"\"
        print("Executing dummy function for: {utterance}")
        return "Executed dummy function"
"""
            functions = {function_name: code}
        
        sequence = [function_name]
    
    return {
        "missing_functions": functions,
        "sequence": sequence,
        "composite_name": composite_name
    }


def create_composite_function(name: str, sequence: List[str]) -> str:
    """Create a composite function that calls a sequence of functions."""
    body_lines = [f"        Catalog.{fn}()" for fn in sequence]
    body = "\n".join(body_lines) if body_lines else "        pass"
    
    return f"""    @staticmethod
    def {name}() -> str:
        \"\"\"Execute a sequence of functions.\"\"\"
{body}
        return "Task completed"
"""


def handle_plan(plan: Dict[str, Any]) -> None:
    """Implement the plan by adding functions to the catalog and reloading."""
    # Add missing functions
    missing = plan.get("missing_functions", {})
    for _, code in missing.items():
        append_to_catalog(code)
    
    # Create composite function if needed
    sequence = plan.get("sequence", [])
    if len(sequence) > 1:
        composite_name = plan.get("composite_name", "run_task")
        composite_code = create_composite_function(composite_name, sequence)
        append_to_catalog(composite_code)
        # Save state to remember what to call after reload
        save_state({"call": composite_name})
    elif len(sequence) == 1:
        # If only one function, just call it directly
        save_state({"call": sequence[0]})
    
    # Reload to apply changes
    reload_self()


async def process_utterance(utterance: str) -> None:
    """Process the user's utterance."""
    if not utterance.strip():
        return
    
    # Check if we have pending tasks from previous run
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
    
    # Generate a plan for implementing the utterance
    plan = await generate_plan(utterance)
    handle_plan(plan)


async def manager(utterance: str, transcriber: Optional[LiveTranscriber] = None) -> None:
    """Entry point for new utterances from the transcriber."""
    print_utterance(utterance)
    await process_utterance(utterance)


def _run_transcriber() -> None:
    """Run the LiveTranscriber."""
    logger.info("Starting LiveTranscriber...")
    tr = LiveTranscriber(callback=manager)
    transcriber_reference["instance"] = tr
    tr.run()
    logger.info("LiveTranscriber stopped")


if __name__ == "__main__":
    _run_transcriber() 