import asyncio
import re
import httpx
import trafilatura


class SearxSearch:
    # Defining each object for the class
    def __init__(
        self,
        base_url: str = "http://localhost:8080",
        headers: dict[str, str] | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.headers = headers or {}

    async def _fetch_and_extract(self, client: httpx.AsyncClient, result: dict) -> str:
        url = result.get("url")
        title = result.get(
            "title", "Untitled"
        )  # Fetches Title key, if not found fallback to Untitled

        if not url:
            return ""

        try:
            response = await client.get(
                url, follow_redirects=True, timeout=10.0, headers=self.headers
            )

            if response.status_code != 200:
                return ""

            content = trafilatura.extract(
                response.text
            )  # Clean the Returned HTML by Trafilatura

            if content:
                # Standardize whitespace

                content = re.sub(r"\n{3,}", "\n\n", content)
                content = re.sub(r"[ \t]+", " ", content).strip()

                return f"TITLE: {title}\nURL: {url}\n\n{content[:2500]}\n"

        except (httpx.HTTPError, asyncio.TimeoutError):
            # Target network errors specifically; drop silently as intended
            pass
        except Exception as e:
            # Catch Unintended errors
            print(f"Extraction error on {url}: {e}")

        return ""

    # Main Async Function for SearxNG
    async def search_async(self, query: str, max_results: int = 3) -> str:
        # Match connection pooling limits to max_results
        limits = httpx.Limits(
            max_connections=max_results + 2, max_keepalive_connections=2
        )

        async with httpx.AsyncClient(limits=limits) as client:
            try:
                response = await client.get(
                    f"{self.base_url}/search",
                    params={"q": query, "format": "json"},  # Calling SearXNG instance
                    timeout=5.0,
                )
                response.raise_for_status()

                data = response.json()
            except Exception as e:
                return f"Search retrieval failed: {e}"

            results = data.get("results", [])[:max_results]
            if not results:
                return "No search results found."

            # Fire concurrent requests

            tasks = [
                self._fetch_and_extract(client, r) for r in results
            ]  # Results as seperate dictionaries in the list as tasks

            extracted_pages = await asyncio.gather(
                *tasks
            )  # Running all tasks in the list at once

            sources = [page for page in extracted_pages if page]
            if not sources:
                return "No usable text could be extracted from top results."

            return "\n\n" + ("\n" + "=" * 80 + "\n").join(sources)

    # Main function called by .agent
    def search(self, query: str, max_results: int = 3) -> str:

        try:
            # Check if there is an active running event loop
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.search_async(query, max_results))

        # If a loop is already running, run the coroutine in that thread/loop context
        if loop.is_running():
            import nest_asyncio

            nest_asyncio.apply()
            return loop.run_until_complete(self.search_async(query, max_results))
        else:
            return loop.run_until_complete(self.search_async(query, max_results))
