# Testing Guide for Meta-Agent Voice Assistant

This guide will help you test the meta-agent voice assistant project.

## Prerequisites

1. Make sure you have an OpenAI API key
2. Have Python 3.9+ installed
3. Have activated the virtual environment

## Quick Start Testing

The simplest way to test the project is to run the standalone runner:

```bash
# Activate the virtual environment
source .venv/bin/activate

# Set your OpenAI API key
export OPENAI_API_KEY=your-api-key-here

# Run the assistant
./run_assistant.py
```

## Testing Steps

1. **Check imports:** Make sure all modules import correctly:

```bash
python -c "import sys; sys.path.append('.'); import new_sub_project.simple_prototype; print('All modules imported successfully!')"
```

2. **Test basic functionality:** Run the assistant and try a simple command:

```bash
./run_assistant.py
```

When it's listening, try saying: "Open Google Chrome" or "Create a text file on the desktop"

3. **Verify catalog modification:** Check that the Catalog class is being extended:

```bash
cat new_sub_project/catalog.py
```

After running some commands, you should see new functions added to the Catalog class.

## Common Issues and Fixes

### Import Errors

If you see `ModuleNotFoundError: No module named 'new_sub_project'`, make sure Python can find the modules:

```bash
# Add the current directory to the Python path
export PYTHONPATH=.
```

### LiveTranscriber Issues

If you have issues with the microphone access:

1. Make sure your microphone is connected and working
2. Check that you have the right permissions
3. Try running with sudo if needed

### OpenAI API Issues

If you have issues with the OpenAI API:

1. Verify your API key is set correctly
2. Check that you have an active subscription with OpenAI
3. Check your internet connection

## Debugging

If you need to debug, you can:

1. Check the log output for errors
2. Examine the state.json file to see what's being saved between reloads
3. Try importing individual components to isolate issues 