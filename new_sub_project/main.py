#!/usr/bin/env python3
"""
Main entry point for the meta-agent prototype.
"""

import asyncio
import logging
import os
import sys

from livetranscriber import LiveTranscriber

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Make sure OpenAI API key is set
if not os.environ.get("OPENAI_API_KEY"):
    logger.error("OPENAI_API_KEY environment variable is not set")
    sys.exit(1)

# Store reference to transcriber to prevent garbage collection
transcriber_reference = {"instance": None}


async def process_command(utterance: str) -> None:
    """Process a voice command."""
    from new_sub_project.simple_prototype import process_command
    await process_command(utterance)


async def manager(utterance: str, transcriber=None) -> None:
    """Entry point for new utterances from the transcriber."""
    logger.info(f"User said: {utterance}")
    await process_command(utterance)


def _run_transcriber() -> None:
    """Run the LiveTranscriber."""
    logger.info("Starting LiveTranscriber...")
    logger.info("Listening for voice commands. Press Ctrl+C to stop.")
    tr = LiveTranscriber(callback=manager)
    transcriber_reference["instance"] = tr
    tr.run()
    logger.info("LiveTranscriber stopped")


def main() -> None:
    """Main entry point."""
    try:
        _run_transcriber()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.exception(f"Error: {e}")


if __name__ == "__main__":
    main() 