from fastapi import FastAPI, UploadFile, HTTPException, File
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse
from pathlib import Path

from app.chat_stream import stream_chat_response
from app.ingestion import ingest_pdf
from app.vector_store import delete_document
from app.journal_store import add_journal, load_journals, delete_journal_record

JOURNAL_DIR = Path("data/journals")
JOURNAL_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI()


class ChatRequest(BaseModel):
    message: str
    thread_id: str
    document_id: str | None = None


@app.get("/health")
def health_check():
    return {
        "status" : "ok"
    }

@app.post("/journals")
async def upload_journal(
    file: UploadFile = File(...)
):
    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are allowed"
        )

    file_path = JOURNAL_DIR / file.filename

    content = await file.read()

    with open(file_path, "wb") as f:
        f.write(content)

    result = ingest_pdf(str(file_path))

    add_journal({
        "document_id": result["document_id"],
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
async def chat(request: ChatRequest):
    return EventSourceResponse(
        stream_chat_response(
            request.message,
            request.thread_id,
            request.document_id,
        )
    )

@app.get("/journals")
def get_journals():
    return {
        "journals": load_journals()
    }

@app.delete("/journals/{document_id}")
def delete_journal(document_id: str):
    journals = load_journals()

    journal = next(
        (
            journal
            for journal in journals
            if journal["document_id"] == document_id
        ),
        None
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

    delete_journal_record(document_id)

    return {
        "message": "Journal Deleted",
        "document_id": document_id
    }
