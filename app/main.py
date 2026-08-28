from fastapi import FastAPI, UploadFile, HTTPException, File
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse
from langchain_core.messages import HumanMessage
from pathlib import Path

from app.ingestion import ingest_pdf
from app.rag_graph import rag_graph
from app.ingestion import ingest_pdf
from app.vector_store import (
    load_vector_store,
    create_retriever,
    delete_document
)
from app.journal_store import add_journal, load_journals, delete_journal_record

JOURNAL_DIR = Path("data/journals")
JOURNAL_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI()

class ChatRequest(BaseModel):
    message: str
    thread_id: str
    document_id: str | None = None


def require_document_id(request: ChatRequest) -> str:
    if request.document_id is None:
        raise HTTPException(
            status_code=400,
            detail="document_id is required for this endpoint"
        )

    return request.document_id


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
    document_id = require_document_id(request)
    config = {
        "configurable": {
            "thread_id": request.thread_id
        }
    }

    async def event_generator():
        async for event in rag_graph.astream_events(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": request.message
                    }
                ],
                "document_id": document_id,
                "search_query": "",
                "context": "",
                "sources": []
            },
            config=config,
            version="v2"
        ):
            if event["event"] == "on_chat_model_stream":
                chunk = event["data"]["chunk"]

                if chunk.content:
                    yield {
                        "event": "message",
                        "data": chunk.content
                    }
        yield {
            "event": "done",
            "data": "[DONE]"
        }

    return EventSourceResponse(
        event_generator()
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
