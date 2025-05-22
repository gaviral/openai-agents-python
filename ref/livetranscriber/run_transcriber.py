import sys
import asyncio
from livetranscriber import LiveTranscriber

def print_callback(text: str):
    # print("TRANSCRIPT:", text)
    print(text)

async def main():
    transcriber = LiveTranscriber.from_defaults(callback=print_callback)

    # Schedule the transcriber's main async function as a task
    transcriber_task = asyncio.create_task(transcriber._run_main())

    # Schedule a task to pause the transcriber after 10 seconds
    async def pause_after_delay(delay):
        await asyncio.sleep(delay)
        print("\nPausing transcriber...")
        transcriber.pause()

    # asyncio.create_task(pause_after_delay(10))

    # Wait for the transcriber task to complete (e.g., when stopped externally)
    await transcriber_task

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nInterrupted – shutting down…") 