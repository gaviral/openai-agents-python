# Meta-Agent Voice Assistant

A dynamic voice assistant that generates and executes functions based on natural language commands.

## Overview

This project uses the OpenAI Agents SDK and LiveTranscriber to create a voice-controlled assistant that can:

1. Listen to user commands via microphone
2. Analyze the commands using an LLM
3. Generate new functions as needed
4. Execute functions in sequence
5. Dynamically expand its capabilities over time

The system maintains a catalog of functions that grows as you use it, following the Single Responsibility Principle.

## Key Features

- **Dynamic Function Generation**: The system automatically creates new functions based on your commands
- **Function Composition**: Complex tasks are broken down into sequences of simple functions
- **State Persistence**: The system remembers what it needs to do after reloading
- **Single Responsibility Principle**: Each function does exactly one thing

## Setup

1. Make sure you have Python 3.9+ installed
2. Create a virtual environment: `uv venv`
3. Activate the environment: `source .venv/bin/activate`
4. Install dependencies: `uv pip install openai-agents livetranscriber`
5. Set your OpenAI API key: `export OPENAI_API_KEY=your-api-key`

## Running the Assistant

```bash
cd new_sub_project
python main.py
```

## Example Commands

- "Open Google Chrome"
- "Create a new text file on the desktop"
- "Send an email to John"
- "Take a screenshot and save it to the desktop"

## Project Structure

- `main.py`: Entry point for the application
- `prototype.py`: Core functionality for the dynamic agent
- `catalog.py`: Contains the growing library of functions
- `function_parser.py`: Extracts function definitions from LLM responses

## How It Works

1. When you speak a command, the LiveTranscriber converts it to text
2. The system checks if it already knows how to handle the command
3. If not, it uses an LLM to generate the necessary functions
4. The functions are added to the catalog
5. The system reloads itself and executes the functions
6. Over time, the catalog grows with more capabilities

## Requirements

- macOS (for the specific function implementations)
- Python 3.9+
- OpenAI API key
- Microphone access 