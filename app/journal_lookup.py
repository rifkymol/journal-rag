from urllib.parse import urlparse

from langchain_tavily import TavilySearch


TRUSTED_SCHOLARLY_DOMAINS = [
    "arxiv.org",
    "pubmed.ncbi.nlm.nih.gov",
    "semanticscholar.org",
    "aclanthology.org",
    "frontiersin.org",
]

LOOKUP_REQUEST_PHRASES = (
    "journal reference",
    "journal references",
    "journal recommendation",
    "journal recommendations",
    "public journal",
    "public journals",
    "find journal",
    "find journals",
    "search journal",
    "search journals",
    "research paper",
    "research papers",
    "academic paper",
    "academic papers",
    "related study",
    "related studies",
    "literature recommendation",
    "literature recommendations",
    "literature review",
    "referensi jurnal",
    "referensi journal",
    "rekomendasi jurnal",
    "artikel ilmiah",
    "paper penelitian",
    "penelitian terkait",
    "cari jurnal",
    "carikan jurnal",
    "jurnal terkait",
    "daftar jurnal",
)

journal_lookup_search: TavilySearch | None = None


def get_journal_lookup_search():
    global journal_lookup_search

    if journal_lookup_search is None:
        journal_lookup_search = TavilySearch(
            max_results=5,
            search_depth="basic",
            include_domains=TRUSTED_SCHOLARLY_DOMAINS,
        )

    return journal_lookup_search


def is_journal_lookup_request(message: str) -> bool:
    normalized_message = message.casefold()

    return any(
        phrase in normalized_message
        for phrase in LOOKUP_REQUEST_PHRASES
    )


def get_source_name(url: str) -> str:
    domain = urlparse(url).netloc.lower()

    if domain.startswith("www."):
        domain = domain[4:]

    return domain


def lookup_related_scholarly_references(query: str):
    result = get_journal_lookup_search().invoke({
        "query": f"{query} academic research paper",
    })

    raw_results = result.get("results", [])
    references = []

    for item in raw_results[:5]:
        url = item.get("url", "")

        references.append({
            "title": item.get("title", "Untitled"),
            "source": get_source_name(url),
            "url": url,
        })

    return references


def format_scholarly_references(references: list[dict]) -> str:
    if not references:
        return "I could not find related scholarly references from the trusted sources."

    lines = [
        f"Here are {len(references)} related scholarly references from trusted sources:",
        "",
    ]

    for index, reference in enumerate(references, start=1):
        title = reference.get("title") or "Untitled"
        source = reference.get("source") or "unknown source"
        url = reference.get("url") or "No URL returned"

        lines.extend([
            f"{index}. {title}",
            f"Source: {source}",
            f"URL: {url}",
            "",
        ])

    return "\n".join(lines).strip()
