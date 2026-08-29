from fastapi import FastAPI, UploadFile, HTTPException, File, Header, Depends
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse
from pathlib import Path

from app.chat_stream import stream_chat_response
from app.ingestion import ingest_pdf
from app.vector_store import delete_document
from app.journal_store import (
    add_journal,
    delete_journal_record,
    get_journal_by_session,
    get_journals_by_session,
)

JOURNAL_DIR = Path("data/journals")
JOURNAL_DIR.mkdir(parents=True, exist_ok=True)
MAX_JOURNALS_PER_SESSION = 3

app = FastAPI()


class ChatRequest(BaseModel):
    message: str
    thread_id: str
    document_id: str | None = None


def require_session_id(
        x_session_id: str = Header(
            ...,
            alias="X-Session-ID"
        )
    ):

    session_id = x_session_id.strip()

    if not session_id:
        raise HTTPException(
            status_code=400,
            detail="Session ID is required"
        )

    return session_id


@app.get("/health")
def health_check():
    return {
        "status" : "ok"
    }

@app.post("/journals")
async def upload_journal(
    file: UploadFile = File(...),
    session_id: str = Depends(
        require_session_id
    )
):
    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are allowed"
        )

    journals = get_journals_by_session(session_id)

    if len(journals) >= MAX_JOURNALS_PER_SESSION:
        raise HTTPException(
            status_code=400,
            detail="You can upload a maximum of 3 PDFs. Delete one PDF before uploading another."
        )

    file_path = JOURNAL_DIR / file.filename

    content = await file.read()

    with open(file_path, "wb") as f:
        f.write(content)

    result = ingest_pdf(
        str(file_path),
        session_id
    )

    add_journal({
        "document_id": result["document_id"],
        "session_id": session_id,
        "filename": file.filename,
        "pages": result["pages"],
        "chunks": result["chunks"]
    })

    return {
        "document_id": result["document_id"],
        "filename": file.filename,
        "pages": result["pages"],
        "chunks": result["chunks"]
    }

@app.post("/chat")
async def chat(
    request: ChatRequest,
    session_id: str = Depends(
        require_session_id
    )
):
    if request.document_id:
        journal = get_journal_by_session(
            request.document_id,
            session_id
        )

        if journal is None:
            raise HTTPException(
                status_code=404,
                detail="Journal not found!"
            )

    return EventSourceResponse(
        stream_chat_response(
            request.message,
            request.thread_id,
            request.document_id,
        )
    )

@app.get("/journals")
def get_journals(
    session_id: str = Depends(
        require_session_id
    )
):
    return {
        "journals": get_journals_by_session(
            session_id
        )
    }

@app.delete("/journals/{document_id}")
def delete_journal(
    document_id: str,
    session_id: str = Depends(
        require_session_id
    )
):
    journal = get_journal_by_session(
        document_id,
        session_id
    )

    if journal is None:
        raise HTTPException(
            status_code=404,
            detail="Journal not found!"
        )

    delete_document(document_id)

    file_path = JOURNAL_DIR / journal["filename"]

    if file_path.exists():
        file_path.unlink()

    delete_journal_record(document_id, session_id)

    return {
        "message": "Journal Deleted",
        "document_id": document_id
    }
