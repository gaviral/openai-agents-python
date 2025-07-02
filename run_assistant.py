#!/usr/bin/env python3
"""
Standalone runner for the meta-agent voice assistant.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add the current directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from livetranscriber import LiveTranscriber

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("assistant.log")
    ]
)
logger = logging.getLogger(__name__)

# Check for OpenAI API key
if not os.environ.get("OPENAI_API_KEY"):
    logger.error("OPENAI_API_KEY environment variable is not set")
    logger.error("Please set it with: export OPENAI_API_KEY=your-api-key")
    sys.exit(1)

# Keep reference to transcriber
transcriber_reference = {"instance": None}


async def process_utterance(utterance: str) -> None:
    """Process the user's utterance."""
    try:
        from new_sub_project.simple_prototype import process_command
        await process_command(utterance)
    except Exception as e:
        logger.exception(f"Error processing utterance: {e}")
        logger.info("Make sure you've installed all dependencies:")
        logger.info("source .venv/bin/activate && uv pip install openai-agents livetranscriber")


async def manager(utterance: str, transcriber=None) -> None:
    """Handle new utterances from the transcriber."""
    logger.info(f"User said: {utterance}")
    await process_utterance(utterance)


def run_transcriber() -> None:
    """Run the voice transcriber."""
    logger.info("Starting LiveTranscriber...")
    logger.info("Listening for voice commands. Press Ctrl+C to stop.")
    try:
        tr = LiveTranscriber(callback=manager)
        transcriber_reference["instance"] = tr
        tr.run()
    except Exception as e:
        logger.exception(f"Error starting transcriber: {e}")
        logger.info("Make sure your microphone is properly connected and you have necessary permissions")
    logger.info("LiveTranscriber stopped")


def check_dependencies() -> bool:
    """Check if all dependencies are installed."""
    try:
        import agents
        import livetranscriber
        return True
    except ImportError as e:
        logger.error(f"Missing dependency: {e}")
        logger.info("Please install all dependencies:")
        logger.info("source .venv/bin/activate && uv pip install openai-agents livetranscriber")
        return False


def main() -> None:
    """Main entry point."""
    print("="*80)
    print("Meta-Agent Voice Assistant")
    print("="*80)
    print("This assistant will listen to your voice commands and execute them.")
    print("Example commands:")
    print("  - Open Google Chrome")
    print("  - Create a text file on the desktop")
    print("\nPress Ctrl+C to exit.")
    print("="*80)
    
    # Make sure new_sub_project directory exists
    if not Path("new_sub_project").exists():
        logger.error("The new_sub_project directory does not exist.")
        logger.error("Please make sure you're running this script from the correct directory.")
        sys.exit(1)
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    try:
        run_transcriber()
    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        logger.exception(f"Error: {e}")


if __name__ == "__main__":
    main() 