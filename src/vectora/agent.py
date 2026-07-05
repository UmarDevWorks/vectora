import json
import time
import httpx

from .search import SearxSearch


class OllamaAgent:
    def __init__(
        self,
        model: str = "gemma4:e2b",
        base_url: str = "http://localhost:11434",
        searx_base_url: str = "http://localhost:8080",
        isthink: bool = True,
    ):
        self.model = model
        self.base_url = base_url.rstrip("/")

        self.searx_base_url = searx_base_url.rstrip("/")
        self.sxsearch = SearxSearch(self.searx_base_url)
        self.isthink = isthink

    def _status(
        self, message: str, progress: int = 0
    ):  # Function for Progress status update for later WebUI implementation
        return {
            "type": "status",
            "message": message,
            "progress": progress,
        }

    # Main Generator Function
    def generate(self, prompt: str, search: bool = False):
        start_time = time.time()

        if not search:
            yield self._status("Thinking...", 10)

            full_prompt = f"User Question:\n{prompt}\n\nProvide a clear, direct answer."

            with httpx.stream(
                "POST",
                f"{self.base_url}/api/generate",  # Calling Ollama instance
                json={
                    "model": self.model,
                    "prompt": full_prompt,
                    "stream": True,
                    "think": self.isthink,
                },
                timeout=120,
            ) as response:
                response.raise_for_status()

                yield self._status("Generating response...", 50)

                # Ignore Empty
                for line in response.iter_lines():
                    if not line:
                        continue

                    try:
                        data = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    if "response" in data:
                        yield {
                            "type": "content",
                            "text": data["response"],
                        }

                    if data.get("done"):  # Stop when Get DONE from Ollama API
                        break

            elapsed = round(time.time() - start_time, 2)
            yield {"type": "done", "elapsed": elapsed}
            return

        # ------------------------------
        # Search Flow (IF SEARCH IS TRUE)
        # ------------------------------
        yield self._status("Analyzing request...", 5)

        yield self._status("Creating search query...", 15)

        # Better system-prompt formatting forcing clean behavior
        searchask_prompt = f"""
<|im_start|>system
You are a search query generator. Convert the user's request into a single concise web search query.
Rules:
- Output ONLY the query.
- No conversational phrases, introductions, or quotes.
- Maximum 8 words.<|im_end|>
<|im_start|>user
{prompt}<|im_end|>
<|im_start|>assistant

"""

        try:
            response = httpx.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": searchask_prompt,
                    "stream": False,
                    "think": self.isthink,
                    # Low temperature reduces conversational jargon
                    "options": {"temperature": 0.1},
                },
                timeout=45,
            )
            response.raise_for_status()
            data = response.json()
            search_prompt = data.get("response", prompt).strip()

            # Strip away unexpected markdown wrap or lines
            search_prompt = search_prompt.replace('"', "").replace("'", "")
            search_prompt = search_prompt.split("\n")[0].strip()
        except Exception:
            search_prompt = prompt

        yield {
            "type": "search_query",
            "query": search_prompt,
        }

        yield self._status("Searching the web...", 35)

        try:
            results = self.sxsearch.search(search_prompt)
        except Exception as e:
            results = f"Search failed: {e}"

        if not results or not str(results).strip():
            results = "No useful search results found."

        yield {
            "type": "search_complete",
            "query": search_prompt,
        }

        yield self._status("Reading sources...", 55)

        combined_prompt = f"""
Context from Web Search:
{str(results)[:4000]}

Using the context above, answer the question comprehensively. If the context is missing or unhelpful, use your pre-existing knowledge.

User Question: {prompt}
"""

        yield self._status("Writing answer...", 75)

        with httpx.stream(
            "POST",
            f"{self.base_url}/api/generate",
            json={
                "model": self.model,
                "prompt": combined_prompt,
                "stream": True,
                "think": self.isthink,
            },
            timeout=120,
        ) as response:
            response.raise_for_status()

            for line in response.iter_lines():
                if not line:
                    continue

                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue

                if "response" in data:
                    yield {
                        "type": "content",
                        "text": data["response"],
                    }

                if data.get("done"):
                    break

        elapsed = round(time.time() - start_time, 2)
        yield self._status("Finished", 100)
        yield {
            "type": "done",
            "elapsed": elapsed,
        }
