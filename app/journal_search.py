from urllib.parse import urlparse

from langchain_tavily import TavilySearch

journal_search = TavilySearch(
    max_results=5,
    search_depth="basic",
    include_domains=[
        "arxiv.org",
        "www.arxiv.org",
        "aclantholoygy.org",
        "semanticscholar.org",
        "pubmed.ncbi.nlm.nih.gov"
    ]
)

def get_source_name(url: str) -> str:
    domain = urlparse(url).netloc.lower()

    if domain.startswith("www."):
        domain = domain[4:]

    return domain

def search_public_journals(query: str):
    result = journal_search.invoke({
        "query": f"{query} research paper"
    })

    raw_results = result.get("results", [])
    journals = []

    for item in raw_results:
        url = item.get("url", "")

        journals.append({
            "title": item.get("title", "Untitled"),
            "url": url,
            "source": get_source_name(url),
            "snippet": item.get("content", "")
        })

    return {
        "results": journals
    }