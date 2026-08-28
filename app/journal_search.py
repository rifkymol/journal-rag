from urllib.parse import urlparse

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
