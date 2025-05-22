"""
livetranscriber.py v0.3.13
---------------------
A zero-dependency **single-file** helper that streams microphone audio to
Deepgram for real-time speech-to-text.  You import :class:`LiveTranscriber`, hand
it a callback, and call :py:meth:`~LiveTranscriber.run`.  Defaults can be
overridden at construction time.

Example
~~~~~~~
>>> from livetranscriber import LiveTranscriber
>>> def on_text(text: str):
...     print("NEW>", text)
...
>>> tr = LiveTranscriber(callback=on_text, model="nova-3-general", language="en-US")
>>> tr.run()  # blocks until you press Ctrl-C

Key features
~~~~~~~~~~~~
* **Simple API** - single `LiveTranscriber` class.
* **Configurable** - every Deepgram *LiveOptions* parameter can be overridden
  via keyword arguments; sensible Nova-3 defaults are provided.
* **Mandatory callback** - forces the calling code to supply a function that
  will be invoked for every *final* transcript chunk (empty / interim chunks
  are ignored).
* **Output capture** - optional `output_path` writes each final transcript
  line to disk.
* **Pause / resume** - you may call :py:meth:`pause` or
  :py:meth:`resume` from your callback.
* **Graceful shutdown** - Ctrl-C or :py:meth:`stop` shuts everything down and
  releases resources.

Environment
~~~~~~~~~~~
Export your Deepgram API key (see https://console.deepgram.com):

    export DEEPGRAM_API_KEY="dg_…"

Python 3.11 is required.
"""

from __future__ import annotations

import asyncio
import contextlib
import os
import queue
import sys
from typing import Callable, Mapping, Any, Optional

import numpy as np
import sounddevice as sd
from deepgram import (
    DeepgramClient,
    DeepgramClientOptions,
    LiveOptions,
    LiveTranscriptionEvents,
)

__all__ = [
    "LiveTranscriber",
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

audio_frame_duration = 0.05  # 50 ms blocks sent to Deepgram

def _default_live_options() -> Mapping[str, Any]:
    """Return *Python* dict of Deepgram LiveOptions defaults.

    Represented as a plain mapping so callers can `**override`.  The mapping
    is converted to :class:`LiveOptions` in :pyclass:`LiveTranscriber`.
    """

    return {
        "model": "nova-3-general",
        "language": "en-US",
        "encoding": "linear16",
        "channels": 1,
        "sample_rate": 16000,
        "punctuate": True,
        "interim_results": False,
        "endpointing": 300,
        "smart_format": True,
        "numerals": False,
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


class LiveTranscriber:
    """High-level wrapper around Deepgram live transcription.

    Parameters
    ----------
    callback:
        A function that will be invoked for **every final transcript**.  The
        callable must accept a single positional `str` argument.  It may be
        sync or `async`.
    output_path:
        Optional path to a text file that will receive each final transcript
        line (UTF-8).
    api_key:
        Your Deepgram API key.  If omitted, the *DEEPGRAM_API_KEY* environment
        variable is used; failing both raises :class:`RuntimeError`.
    keepalive:
        If *True* (default) the WebSocket client sends keepalive pings - this
        is Deepgram's recommended production setting.
    **live_options_overrides:
        Any keyword argument that matches a *LiveOptions* field overrides the
        built-in defaults.  For example, ``punctuate=False``.
    """

    def __init__(
        self,
        *,
        callback: Callable[[str], Any],
        output_path: str | os.PathLike | None = None,
        api_key: Optional[str] = None,
        keepalive: bool = True,
        **live_overrides: Any,
    ) -> None:
        if callback is None:
            raise TypeError("callback parameter is required")
        self._callback = callback

        # Work out API key early so we fail fast.
        self._api_key = api_key or os.getenv("DEEPGRAM_API_KEY")
        if not self._api_key:
            raise RuntimeError("Deepgram API key missing – set DEEPGRAM_API_KEY or pass api_key=")

        # Merge caller overrides onto defaults – later keys win.
        opts = {**_default_live_options(), **live_overrides}
        self._live_opts = LiveOptions(**opts)  # type: ignore[arg-type]

        client_opts = DeepgramClientOptions(options={"keepalive": "true"}) if keepalive else None
        self._dg_client = DeepgramClient(self._api_key, client_opts)
        self._ws = self._dg_client.listen.websocket.v("1")

        self._loop: asyncio.AbstractEventLoop | None = None
        self._done_evt = asyncio.Event()
        self._finishing = False
        self._keyboard_interrupt_received = False

        # Mic/audio plumbing
        self._audio_q: "queue.Queue[np.ndarray]" = queue.Queue()
        self._mic: sd.InputStream | None = None
        self._sender_task: asyncio.Task | None = None

        # Output file handle (opened lazily on first write).
        self._output_path = os.fspath(output_path) if output_path else None
        self._out_fp: Optional[open] = None

        # Public state
        self.paused: bool = False

    # ------------------------------------------------------------------
    # Control helpers
    # ------------------------------------------------------------------

    def stop(self) -> None:
        """Public request to shut down; may be called from any thread."""
        if self._finishing:
            return
        self._finishing = True
        print("\nShutting down…") # Print shutdown message once

        if self._loop and not self._loop.is_closed():
            # First start the cleanup in the background
            asyncio.run_coroutine_threadsafe(self._finish_and_cleanup(), self._loop)
            
            # Signal the main wait loop that it's done
            self._loop.call_soon_threadsafe(self._done_evt.set)
        else:
            # Fallback if loop is not available or closed
            asyncio.run(self._finish_and_cleanup())

    def pause(self) -> None:
        """Pause writing transcripts to *output_path* (callback still runs)."""
        self.paused = True

    def resume(self) -> None:
        """Resume writing transcripts to *output_path*."""
        self.paused = False

    # ------------------------------------------------------------------
    # User‑facing entry point (blocking)
    # ------------------------------------------------------------------

    def run(self) -> None:  # noqa: D401 (imperative OK)
        """Run until `.stop()` or Ctrl-C."""
        try:
            asyncio.run(self._run_main())
        except KeyboardInterrupt:
            print("\nInterrupted – shutting down…")
            self._keyboard_interrupt_received = True
            self.stop()
            asyncio.run(self._wait_for_cleanup())

    async def _wait_for_cleanup(self):
        """Block in a fresh event loop until `_done_evt` set."""
        while not self._done_evt.is_set():
            await asyncio.sleep(0.05)

    # ------------------------------------------------------------------
    # Internals – async logic lives here
    # ------------------------------------------------------------------

    async def _run_main(self):  # noqa: C901 (acceptable in single file)
        self._loop = asyncio.get_running_loop()

        self._ws.on(LiveTranscriptionEvents.Open, self._on_open)
        self._ws.on(LiveTranscriptionEvents.Transcript, self._on_transcript)
        self._ws.on(LiveTranscriptionEvents.Error, self._on_error)
        self._ws.on(LiveTranscriptionEvents.Close, self._on_close)

        self._ws.start(self._live_opts)
        self._mic = sd.InputStream(
            channels=1,
            samplerate=self._live_opts.sample_rate,
            dtype=np.int16,
            blocksize=int(self._live_opts.sample_rate * audio_frame_duration),
            callback=self._on_audio,
        )
        self._mic.start()
        print("🎤  Listening – speak now… (Ctrl‑C to quit)")

        # Launch background task that pushes audio frames into the WS.
        self._sender_task = asyncio.create_task(self._send_audio())

        # Wait until shutdown (`_done_evt` is set).
        try:
            # Await the event that will be set by _finish_and_cleanup
            await self._done_evt.wait()
            
            # Once _done_evt is set, ensure cleanup is complete before exiting
            if self._finishing:
                try:
                    # Allow a little time for cleanup to finish
                    await asyncio.sleep(0.5)
                    print("✓ Exiting gracefully")
                except asyncio.CancelledError:
                    pass
        finally:
            # If _done_evt was set, cleanup should already be running or done
            if not self._finishing and not self._keyboard_interrupt_received:
                await self._finish_and_cleanup()

    # ---------------------------------------------------------------------
    # Deepgram event callbacks (sync)
    # ---------------------------------------------------------------------

    # Each handler signature must match expected Deepgram signature – we accept
    # *args and **kwargs to stay version‑tolerant.

    def _on_open(self, *_):
        print("🟢  Deepgram connection established")

    def _on_transcript(self, _client, result, **_):
        # We only act on *final* transcripts; ignore interim / empty chunks
        text = result.channel.alternatives[0].transcript.strip()
        if not text:
            return

        # Fire the user callback – sync or async.
        maybe_coro = self._callback(text)
        if asyncio.iscoroutine(maybe_coro):
            asyncio.create_task(maybe_coro)  # fire‑and‑forget

        # Optionally write to disk.
        if self._output_path and not self.paused:
            if self._out_fp is None:
                self._out_fp = open(self._output_path, "a", encoding="utf-8")
            self._out_fp.write(text + "\n")
            self._out_fp.flush()

    def _on_error(self, _client, exc, **_):
        print(f"❌  Deepgram error: {exc}")
        self.stop()

    def _on_close(self, *_):
        # Connection closure is part of the cleanup; don't print here
        self.stop()

    # ---------------------------------------------------------------------
    # Mic callback – keeps RT‑safe path minimal and lock‑free.
    # ---------------------------------------------------------------------

    def _on_audio(self, indata, *_):
        self._audio_q.put_nowait(indata.copy())

    # ---------------------------------------------------------------------
    # Background task that ships audio frames to Deepgram.
    # ---------------------------------------------------------------------

    async def _send_audio(self):  # noqa: D401 (imperative OK)
        try:
            while not self._finishing:
                try:
                    frame = self._audio_q.get_nowait()
                except queue.Empty:
                    await asyncio.sleep(0.002)
                    continue
                self._ws.send(frame.tobytes())
        except asyncio.CancelledError:
            pass

    # ------------------------------------------------------------------
    # Cleanup logic – safe to call multiple times
    # ------------------------------------------------------------------

    async def _finish_and_cleanup(self):
        # Stop sender first so we don't race with finish().
        if self._sender_task and not self._sender_task.done():
            self._sender_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._sender_task

        # Mic
        if self._mic:
            self._mic.stop()
            self._mic.close()
            self._mic = None # Mark mic as cleaned up

        # Deepgram session
        # Ensure finish is called only once
        if self._ws:
            try:
                await asyncio.to_thread(self._ws.finish)
            except Exception as exc:  # noqa: BLE001 (broad OK – just logging)
                print(f"⚠️  Error during WS finish: {exc}")
            finally:
                self._ws = None # Mark websocket as cleaned up

        # File
        if self._out_fp:
            self._out_fp.close()
            self._out_fp = None # Mark file as cleaned up

        # Ensure this is always called to signal completion
        if not self._done_evt.is_set():
            self._done_evt.set()
            print("✓ Cleanup completed")


# ---------------------------------------------------------------------------
# Strongly‑typed convenience factory (optional): LiveTranscriber.from_defaults()
# ---------------------------------------------------------------------------

    @classmethod
    def from_defaults(
        cls,
        callback: Callable[[str], Any],
        **overrides: Any,
    ) -> "LiveTranscriber":
        """Alternate constructor mirroring :pyclass:`__init__` but without *api_key*.

        The primary motivation is terseness in simple scripts:

            tr = LiveTranscriber.from_defaults(on_text)
            tr.run()

        """
        return cls(callback=callback, **overrides)


if __name__ == "__main__":
    # This block allows the script to be run directly from the command line
    # using the entry point defined in pyproject.toml
    import argparse

    parser = argparse.ArgumentParser(description="Live transcribe audio using Deepgram.")
    parser.add_argument(
        "--output",
        help="Optional path to a text file to save the transcript."
    )
    parser.add_argument(
        "--model",
        default="nova-3-general",
        help="Deepgram model to use (default: nova-3-general)."
    )
    parser.add_argument(
        "--language",
        default="en-US",
        help="Language for transcription (default: en-US)."
    )

    args = parser.parse_args()

    def print_text(text: str):
        print("NEW>", text)

    # Initialize and run the transcriber with command-line arguments
    transcriber = LiveTranscriber.from_defaults(
        callback=print_text,
        output_path=args.output,
        model=args.model,
        language=args.language
    )

    transcriber.run()
