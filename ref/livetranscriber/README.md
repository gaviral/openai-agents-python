# livetranscriber

A single-file helper with minimal external dependencies that streams microphone audio to Deepgram for real-time speech-to-text. This is available as a package on PyPI.

## Features

*   **Simple API** - single `LiveTranscriber` class.
*   **Configurable** - every Deepgram *LiveOptions* parameter can be overridden via keyword arguments; sensible Nova-3 defaults are provided.
*   **Mandatory callback** - forces the calling code to supply a function that will be invoked for every *final* transcript chunk (empty / interim chunks are ignored).
*   **Output capture** - optional `output_path` writes each final transcript line to disk.
*   **Pause / resume** - you may call `pause` or `resume` from your callback.
*   **Graceful shutdown** - Ctrl-C or `stop` shuts everything down and releases resources.

## Installation

Install the package directly from PyPI using pip:

```bash
pip install livetranscriber
```

Alternatively, if you are working with the source code or a specific requirements file, you can install the dependencies listed in `requirements.txt`:

```
deepgram-sdk>=4,<5
numpy>=1.24  # build-time requirement of sounddevice
sounddevice>=0.4
```

Install with `uv` (preferred) or plain `pip`:

```bash
uv venv .venv && source .venv/bin/activate
uv pip install -r requirements.txt
```
or
```bash
pip install -r requirements.txt
```

2.  **Python Version:**

    Python 3.11 is required.

## Environment Setup

Export your Deepgram API key (see https://console.deepgram.com). For persistent access, add the following line to your shell profile file (e.g., `~/.zshrc`, `~/.bashrc`, or `~/.profile`) and restart your terminal or source the file:

```bash
export DEEPGRAM_API_KEY="dg_…"
```

## Example Usage

Here are examples demonstrating how to use the `livetranscriber` package.

### Minimal Example

A basic example showing the essential setup:

```python
from livetranscriber import LiveTranscriber

def simple_callback(text: str):
    print("NEW >", text)

tr = LiveTranscriber(callback=simple_callback)
tr.run()
```

### Comprehensive Example

A more detailed example demonstrating various features like output to file and pause/resume:

```python
import time
from livetranscriber import LiveTranscriber

def comprehensive_callback(text: str):
    print("Transcript received:", text)

    # Example: Pause transcription if a specific phrase is detected
    if "pause recording" in text.lower():
        print("Status: PAUSING...")
        transcriber.pause()
        print("Status: RECORDING PAUSED. Say 'resume recording' to continue.")

    # Example: Resume transcription if another phrase is detected
    if "resume recording" in text.lower():
        print("Status: RESUMING...")
        transcriber.resume()
        print("Status: RECORDING RESUMED.")

    # Example: Stop transcription if a stop phrase is detected
    if "stop recording" in text.lower():
        print("Status: STOPPING...")
        transcriber.stop()

# Instantiate with various options
output_file = "transcript_output.txt"
transcriber = LiveTranscriber(
    callback=comprehensive_callback,
    output_path=output_file, # Output transcript to a file
    model="nova-3-general", # Specify a model
    language="en-US",     # Specify a language
    punctuate=True,         # Enable punctuation
    smart_format=True       # Enable smart formatting (like numbers)
)

try:
    print(f"Starting transcription. Transcript will also be saved to {output_file}")
    print("Instructions: Press Ctrl+C to stop, or say 'pause recording', 'resume recording', or 'stop recording'.")
    transcriber.run() # Blocks until stop() is called or Ctrl-C is pressed
except KeyboardInterrupt:
    print("\nInterrupted by user. Stopping.")
finally:
    print("Transcription session ended.")
```

## API

### `LiveTranscriber` Class

High-level wrapper around Deepgram live transcription.

**Parameters:**

*   `callback`: A function that will be invoked for every final transcript. Must accept a single `str` argument. May be sync or async.
*   `output_path` (Optional): Path to a text file that will receive each final transcript line (UTF-8).
*   `api_key` (Optional): Your Deepgram API key. If omitted, the `DEEPGRAM_API_KEY` environment variable is used; failing both raises `RuntimeError`.
*   `keepalive` (Optional): If `True` (default) the WebSocket client sends keepalive pings.
*   `**live_options_overrides` (Optional): Any keyword argument that matches a *LiveOptions* field overrides the built-in defaults. For example, `punctuate=False`.

**Methods:**

*   `run()`: Run until `.stop()` or Ctrl-C.
*   `stop()`: Public request to shut down; may be called from any thread.
*   `pause()`: Pause writing transcripts to `output_path`. Note that the callback function will continue to receive transcription data while paused.
*   `resume()`: Resume writing transcripts to `output_path`.

## Development Standards

This section outlines the standards and practices for contributing to `livetranscriber`.

This project is distributed under the [MIT License](LICENSE).

### Tagging

After pushing a new version commit, always create a Git tag for that version and push the tag. For version `x.y.z`, the tag name should be `vx.y.z`.

## Dependencies

*   `deepgram-sdk`
*   `numpy`
*   `sounddevice`
