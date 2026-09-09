from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile

from app.ingestion import ingest_pdf, ingest_text
from app.models import SourceTextRequest
from app.source_store import add_source, delete_source, get_source, list_sources
from app.vector_store import delete_document, load_vector_store


MAX_SOURCE_BYTES = 20 * 1024 * 1024
MAX_SOURCES_PER_SESSION = 3


def public_source(source: dict) -> dict:
    return {
        key: value
        for key, value in source.items()
        if key not in {"session_id", "storage_path"}
    }


async def create_pdf_source(
    file: UploadFile,
    session_id: str,
    storage_dir: Path,
    existing_count: int,
) -> dict:
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

if existing_count >= MAX_SOURCES_PER_SESSION:
    raise HTTPException(
        status_code=400,
        detail="You can create a maximum of 3 sources per session. Delete one before adding another.",
    )

    original_name = Path(file.filename or "journal.pdf").name
    if not original_name.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="The PDF file is empty")
    if len(content) > MAX_SOURCE_BYTES:
        raise HTTPException(status_code=413, detail="The PDF file must be smaller than 20 MB")

    storage_dir.mkdir(parents=True, exist_ok=True)
    document_id = str(uuid4())
    storage_path = storage_dir / f"{document_id}.pdf"
    storage_path.write_bytes(content)

    try:
        result = ingest_pdf(str(storage_path), session_id)
        source = add_source({
            "document_id": result["document_id"],
            "session_id": session_id,
            "source_type": "pdf",
            "title": original_name,
            "filename": original_name,
            "pages": result["pages"],
            "chunks": result["chunks"],
            "storage_path": str(storage_path),
        })
        return public_source(source)
    except Exception:
        storage_path.unlink(missing_ok=True)
        raise


def create_text_source(request: SourceTextRequest, session_id: str) -> dict:
    result = ingest_text(request.text, request.title, session_id, request.language)
    source = add_source({
        "document_id": result["document_id"],
        "session_id": session_id,
        "source_type": "text",
        "title": request.title,
        "filename": None,
        "pages": result["pages"],
        "chunks": result["chunks"],
        "language": request.language,
    })
    return public_source(source)


def get_sources(session_id: str) -> list[dict]:
    return [public_source(source) for source in list_sources(session_id)]


def delete_source_for_session(source_id: str, session_id: str) -> dict | None:
    source = get_source(source_id, session_id)
    if source is None:
        return None

    delete_document(source_id)
    storage_path = source.get("storage_path")
    if storage_path:
        Path(storage_path).unlink(missing_ok=True)
    elif source.get("filename"):
        # Clean up records created before generated storage paths were introduced.
        (Path("data/journals") / Path(source["filename"]).name).unlink(missing_ok=True)
    delete_source(source_id, session_id)
    return public_source(source)


def get_source_preview(source_id: str, session_id: str, page: int) -> dict | None:
    source = get_source(source_id, session_id)
    if source is None:
        return None

    if page < 1:
        raise HTTPException(status_code=400, detail="Page must be greater than zero")

    result = load_vector_store().get(
        where={"document_id": source_id},
        include=["documents", "metadatas"],
    )
    documents = []
    for content, metadata in zip(result.get("documents", []), result.get("metadatas", [])):
        if int(metadata.get("page", 0)) + 1 == page:
            documents.append(content)

    return {
        "source": public_source(source),
        "page": page,
        "text": "\n\n".join(documents),
    }
