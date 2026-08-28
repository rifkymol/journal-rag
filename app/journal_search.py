from urllib.parse import urlparse

from langchain_core.tools import tool
from langchain_tavily import TavilySearch


journal_search = TavilySearch(
    max_results=5,
    search_depth="basic",
)


def get_source_name(url: str) -> str:
    domain = urlparse(url).netloc.lower()

    if domain.startswith("www."):
        domain = domain[4:]

    return domain


def search_public_journals(query: str):
    result = journal_search.invoke({
        "query": f"{query} academic research paper journal"
    })

    raw_results = result.get("results", [])

    journals = []

    for item in raw_results[:5]:
        url = item.get("url", "")

        journals.append({
            "title": item.get("title", "Untitled"),
            "url": url,
            "source": get_source_name(url),
        })

    return {
        "results": journals
    }


@tool("search_public_journals")
def search_public_journals_tool(query: str):
    """
    Search for public academic journal or research paper references.

    Use this tool when the user asks for journal references,
    research papers, academic papers, or related literature.

    Returns up to 5 related journal references with title, source, and URL.
    """

    return search_public_journals(query)
