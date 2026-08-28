from fastapi import FastAPI, UploadFile, HTTPException, File
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse
from pathlib import Path

from app.ingestion import ingest_pdf
from app.rag_graph import rag_graph
from app.vector_store import delete_document
from app.journal_store import add_journal, load_journals, delete_journal_record
from app.journal_search import search_public_journals
from app.journal_import import import_public_journal

JOURNAL_DIR = Path("data/journals")
JOURNAL_DIR.mkdir(parents=True, exist_ok=True)

REFERENCE_REQUEST_PHRASES = (
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
    "5 jurnal",
    "lima jurnal",
)

app = FastAPI()


class ChatRequest(BaseModel):
    message: str
    thread_id: str
    document_id: str | None = None


class JournalSearchRequest(BaseModel):
    query: str


class JournalImportSearch(BaseModel):
    url: str


def is_journal_reference_request(message: str) -> bool:
    normalized_message = message.casefold()

    return any(
        phrase in normalized_message
        for phrase in REFERENCE_REQUEST_PHRASES
    )


def format_journal_references(search_results: dict) -> str:
    journals = search_results.get("results", [])

    if not journals:
        return "I could not find public journal references for that query."

    lines = [
        f"Here are {len(journals)} public journal references I found:",
        "",
    ]

    for index, journal in enumerate(journals, start=1):
        title = journal.get("title") or "Untitled"
        source = journal.get("source") or "unknown source"
        url = journal.get("url") or "No URL returned"

        lines.extend([
            f"{index}. {title}",
            f"Source: {source}",
            f"URL: {url}",
            "",
        ])

    return "\n".join(lines).strip()


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
    if is_journal_reference_request(request.message):
        async def reference_event_generator():
            try:
                search_results = search_public_journals(request.message)
                answer = format_journal_references(search_results)
            except Exception:
                answer = (
                    "I could not search public journal references. "
                    "Please check that TAVILY_API_KEY is configured."
                )

            yield {
                "event": "message",
                "data": answer
            }
            yield {
                "event": "done",
                "data": "[DONE]"
            }

        return EventSourceResponse(
            reference_event_generator()
        )

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
            metadata = event.get("metadata") or {}

            if (
                event["event"] == "on_chat_model_stream"
                and metadata.get("langgraph_node") == "generate"
            ):
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

@app.post("/journals/search")
def search_journals(request: JournalSearchRequest):
    return search_public_journals(
        request.query
    )

# @app.post("/journals/import")
# def import_journal(
#     request: JournalImportSearch
# ):
#     try:
#         result = import_public_journal(
#             request.url
#         )

#         return result

#     except ValueError as error:
#         raise HTTPException(
#             status_code=400,
#             detail=str(error)
#         )

#     except Exception:
#         raise HTTPException(
#             status_code=500,
#             detail="Failed to import journal"
#         )


