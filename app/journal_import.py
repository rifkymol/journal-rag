from pathlib import Path
from urllib.parse import urlparse

import requests

from app.ingestion import ingest_pdf
from app.journal_url_resolver import resolve_pdf_url

JOURNAL_DIR = Path("data/journals")
JOURNAL_DIR.mkdir(parents=True, exist_ok=True)


def import_public_journal(url: str):
    pdf_url = resolve_pdf_url(url)

    response = requests.get(
        pdf_url,
        timeout=30
    )

    response.raise_for_status()

    content_type = response.headers.get(
        "content-type",
        ""
    )

    if "application/pdf" not in content_type:
        raise ValueError(
            "URL does not point to a PDF"
        )

    parsed_url = urlparse(url)

    filename = Path(
        parsed_url.path
    ).name

    if not filename.endswith(".pdf"):
        filename = f"{filename}".pdf

    file_path = JOURNAL_DIR / filename

    with open(file_path, "wb") as file:
        file.write(response.content)

    result = ingest_pdf(
        str(file_path)
    )

    return {
        "document_id": result["document_id"],
        "filename": filename,
        "pages": result["pages"],
        "chunks": result["chunks"]
    }