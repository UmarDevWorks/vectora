# Vectora

![Vectora](vectora.png)

Vectora is a small Python package for retrieval-augmented generation built around two local services:

- Ollama for streamed text generation
- SearxNG for web search and source extraction

The package exposes a single high-level agent, OllamaAgent, that can answer prompts directly or run a web-search-first workflow before generating a response.

## Features

- Streamed chat responses from an Ollama model
- Optional search pipeline through a SearxNG instance
- Async source fetching and text extraction with trafilatura
- Event-based output for status updates, search queries, content chunks, and completion

## Requirements

- Python 3.11 or newer
- A running Ollama server
- A running SearxNG instance

The default endpoints used by the code are:

- Ollama: http://localhost:11434
- SearxNG: http://localhost:8080

## Installation

Install the package and its dependencies from the project root:

```bash
pip install .
```

For development dependencies:

```bash
pip install .[dev]
```

For the Flask web UI demo:

```bash
pip install .[web]
```

## Quick Start

```python
from vectora import OllamaAgent

agent = OllamaAgent(
		model="gemma4:e2b",
		base_url="http://localhost:11434",
		searx_base_url="http://localhost:8080",
)

for event in agent.generate("What is retrieval augmented generation?", search=True):
		print(event)
```

## How It Works

OllamaAgent.generate() yields a stream of structured events:

- status - progress updates for UI feedback
- search_query - the generated web search query
- search_complete - emitted after search results are gathered
- content - streamed response chunks from Ollama
- done - final completion event with elapsed time

When search=False, the agent sends the prompt directly to Ollama. When search=True, it:

1. Uses Ollama to turn the user request into a concise search query
2. Queries SearxNG for web results
3. Fetches and extracts readable text from the top result pages
4. Sends the collected context back to Ollama to produce the final answer

## Public API

### vectora.OllamaAgent

Defined in [src/vectora/agent.py](src/vectora/agent.py).

```python
OllamaAgent(
		model: str = "gemma4:e2b",
		base_url: str = "http://localhost:11434",
		searx_base_url: str = "http://localhost:8080",
		isthink: bool = True,
)
```

#### generate(prompt: str, search: bool = False)

Returns a generator that yields dictionaries with the event types listed above.

### vectora.search.SearxSearch

Defined in [src/vectora/search.py](src/vectora/search.py).

```python
SearxSearch(base_url: str = "http://localhost:8080")
```

The search client accepts an optional `headers` mapping. If you do not pass one, it uses an empty header set and sends no default `User-Agent`.

```python
SearxSearch(
	base_url: str = "http://localhost:8080",
	headers: dict[str, str] | None = None,
)
```

#### search(query: str, max_results: int = 3)

Returns extracted text from top search results as a single string.


## Notes

- The search pipeline depends on SearxNG returning JSON at /search?format=json.
- search=True is intended for answer augmentation, not as a standalone browser replacement.
- The package uses nest_asyncio so the search client can run both inside and outside an active event loop.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for the full text.
