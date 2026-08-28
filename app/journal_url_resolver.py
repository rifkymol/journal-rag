from urllib.parse import urlparse

ALLOWED_DOMAINS = {
    "arxiv.org",
    "www.arxiv.org",
}

def resolve_pdf_url(url: str) -> str:
    parsed = urlparse(url)

    domain = parsed.netloc.lower()

    if domain not in ALLOWED_DOMAINS:
        raise ValueError(
            "Unsupported journal source"
        )

    if domain in {
        "arxiv.org",
        "www.arxiv.org",
    }:
        return resolve_arvix_url(url)

    return url

def resolve_arvix_url(url: str) -> str:
    if "/pdf/" in url:
        return url

    if "/abs/" in url:
        paper_id = url.split("/abs/")[-1]

        return f"https://arvix.org/pdf/{paper_id}"

    return url