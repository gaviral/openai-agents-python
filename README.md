# Meta-Agent Voice Assistant

A dynamic voice assistant that generates and executes functions based on natural language commands. The system automatically expands its capabilities by creating new functions on-the-fly.

## Features

- **Voice Control**: Speak commands naturally, and the assistant will execute them
- **Dynamic Function Generation**: The system creates new functions as needed
- **Self-Expanding Catalog**: The catalog of available functions grows over time
- **Single Responsibility**: Each function follows the Single Responsibility Principle
- **Function Composition**: Complex tasks are broken down into simpler ones

## Getting Started

### Prerequisites

- Python 3.9 or higher
- macOS (for the specific function implementations)
- OpenAI API key
- Microphone access

### Installation

1. Clone this repository
   ```bash
   git clone https://github.com/yourusername/meta-agent-assistant.git
   cd meta-agent-assistant
   ```

2. Create and activate a virtual environment
   ```bash
   uv venv
   source .venv/bin/activate
   ```

3. Install dependencies
   ```bash
   uv pip install openai-agents livetranscriber
   ```

4. Set your OpenAI API key
   ```bash
   export OPENAI_API_KEY=your-api-key
   ```

### Running the Assistant

Simply run the standalone runner script:
```bash
./run_assistant.py
```

The assistant will start listening for your voice commands. Try saying:
- "Open Google Chrome"
- "Create a text file on the desktop"

## How It Works

1. The system listens for voice commands using LiveTranscriber
2. When a command is received, it checks if it already knows how to handle it
3. If not, it uses an LLM (via OpenAI Agents SDK) to generate the necessary functions
4. The functions are added to the Catalog class
5. The system reloads itself and executes the functions
6. Over time, the Catalog grows with more capabilities

## Project Structure

- `new_sub_project/`: Main project module
  - `catalog.py`: Contains the Catalog class that gets dynamically extended
  - `simple_prototype.py`: Simplified implementation of the meta-agent
  - `function_parser.py`: Extracts function definitions from LLM responses
- `run_assistant.py`: Standalone runner script
- `TESTING.md`: Guide for testing the project

## Troubleshooting

See the [Testing Guide](TESTING.md) for troubleshooting tips and common issues.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- OpenAI for the Agents SDK
- The developers of LiveTranscriber
- The Python community for the excellent tools and libraries 