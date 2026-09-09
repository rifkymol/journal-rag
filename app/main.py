from pathlib import Path

from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile
from sse_starlette.sse import EventSourceResponse

from app.chat_stream import stream_chat_response
from app.journal_store import get_journal_by_session, get_journals_by_session
from app.models import ChatRequest, SourceTextRequest
from app.observability import flush_langfuse
from app.source_service import (
    MAX_SOURCES_PER_SESSION,
    create_pdf_source,
    create_text_source,
    delete_source_for_session,
    get_source_preview,
    get_sources,
)

JOURNAL_DIR = Path("data/journals")
JOURNAL_DIR.mkdir(parents=True, exist_ok=True)
app = FastAPI()


def require_session_id(
    x_session_id: str = Header(..., alias="X-Session-ID"),
):
    session_id = x_session_id.strip()
    if not session_id:
        raise HTTPException(status_code=400, detail="Session ID is required")
    return session_id


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.on_event("shutdown")
def shutdown_langfuse():
    flush_langfuse()

@app.post("/journals")
async def upload_journal(
    file: UploadFile = File(...),
    session_id: str = Depends(require_session_id),
):
    return await create_pdf_source(
        file,
        session_id,
        JOURNAL_DIR,
        len(get_journals_by_session(session_id)),
    )


@app.post("/sources/pdf")
async def upload_source_pdf(
    file: UploadFile = File(...),
    session_id: str = Depends(require_session_id),
):
    return await create_pdf_source(
        file,
        session_id,
        JOURNAL_DIR,
        len(get_journals_by_session(session_id)),
    )


@app.post("/sources/text")
def create_text_source_endpoint(
    request: SourceTextRequest,
    session_id: str = Depends(require_session_id),
):
    if len(get_journals_by_session(session_id)) >= MAX_SOURCES_PER_SESSION:
        raise HTTPException(
            status_code=400,
            detail="You can create a maximum of 3 sources per session. Delete one before adding another.",
        )
    return create_text_source(request, session_id)


@app.get("/sources")
def get_sources_endpoint(session_id: str = Depends(require_session_id)):
    return {"sources": get_sources(session_id)}


@app.get("/sources/{source_id}/preview")
def preview_source_endpoint(
    source_id: str,
    page: int = 1,
    session_id: str = Depends(require_session_id),
):
    preview = get_source_preview(source_id, session_id, page)
    if preview is None:
        raise HTTPException(status_code=404, detail="Source not found")
    return preview


@app.delete("/sources/{source_id}")
def delete_source_endpoint(
    source_id: str,
    session_id: str = Depends(require_session_id),
):
    source = delete_source_for_session(source_id, session_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Source not found")
    return {"message": "Source deleted", "source_id": source_id}

@app.post("/chat")
async def chat(
    request: ChatRequest,
    session_id: str = Depends(require_session_id),
):
    for document_id in request.document_ids:
        if get_journal_by_session(document_id, session_id) is None:
            raise HTTPException(status_code=404, detail="Source not found!")

    return EventSourceResponse(
        stream_chat_response(
            request.message,
            request.thread_id,
            request.document_ids,
            session_id,
            request.mode,
            request.language,
        )
    )

@app.get("/journals")
def get_journals(
    session_id: str = Depends(require_session_id),
):
    return {"journals": get_sources(session_id)}

@app.delete("/journals/{document_id}")
def delete_journal(
    document_id: str,
    session_id: str = Depends(require_session_id),
):
    if get_journal_by_session(document_id, session_id) is None:
        raise HTTPException(status_code=404, detail="Journal not found!")

    delete_source_for_session(document_id, session_id)
    return {"message": "Journal Deleted", "document_id": document_id}
