from fastapi import FastAPI, UploadFile, HTTPException, File
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse
from langchain_core.messages import HumanMessage
from pathlib import Path

from app.ingestion import ingest_pdf
from app.rag_graph import rag_graph
from app.llm import ask_llm
from app.document_loader import load_pdf
from app.text_splitter import split_documents
from app.rag import ask_rag
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
    document_id: str


@app.get("/health")
def health_check():
    return {
        "status" : "ok"
    }

@app.post("/chat")
def chat(request: ChatRequest):
    answer = ask_llm(request.message)

    return {
        "answer": answer
    }

# untuk meload pdf
@app.get("/test-pdf")
def test_pdf():
    documents = load_pdf("data/journals/sample.pdf")

    return {
        "total_pages": len(documents),
        "first_page": documents[0].page_content[:500]
    }

# untuk memotong dokumen menjadi beberapa chunks
@app.get("/test-chunks")
def test_chunks():
    documents = load_pdf("data/journals/sample.pdf")
    chunks = split_documents(documents)

    return {
        "total_pages": len(documents),
        "total_chunks": len(chunks),
        "first_chunk": chunks[0].page_content,
        "first_chunk_metadata": chunks[0].metadata
    }

# untuk mencoba mencari jawaban dari chunks yang relevant berdasarkan pertanyaan
# @app.get("/test-search")
# def test_search():
#     #  load document
#     documents = load_pdf("data/journals/sample.pdf")

#     #  ini buat memotong dokumen menjadi chunks
#     chunks = split_documents(documents)

#     #  mengubah chunks menjadi vector
#     vector_store = create_vector_store(chunks)

#     # dari pertanyaan diubah ke vector dan melakukan similarity search
#     # k= adalah berapa banyak chunks yang memiliki makna yang sama dengan pertanyaan yang akan diambil
#     results = vector_store.similarity_search(
#         "What is the main objective of this research",
#         k=3
#     )

#     return {
#         "results": [
#             {
#                 "content": document.page_content,
#                 "metadata": document.metadata
#             }
#             for document in results
#         ]
#     }

# @app.get("/test-retriever")
# def test_retriever():
    documents = load_pdf("data/journals/sample.pdf")

    chunks = split_documents(documents)

    vectore_store = create_vector_store(chunks)

    retriever = create_retriever(vectore_store)

    results = retriever.invoke(
        "What is the main objective of this research?"
    )

    return {
        "results": [
            {
                "content": document.page_content,
                "metadata": document.metadata
            }
            for document in results
        ]
    }

@app.post("/rag-chat")
def test_rag(request: ChatRequest):
    vectore_store = load_vector_store()
    retriever = create_retriever(vectore_store)

    results = ask_rag(
        request.message, 
        retriever
    )
    return results

@app.post("/ingest")
def ingest():
    result = ingest_pdf(
        "data/journals/sample.pdf"
    )

    return result

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


@app.post("/graph-chat")
def graph_chat(request: ChatRequest):
    config = {
        "configurable": {
            "thread_id": request.thread_id
        }
    }

    result = rag_graph.invoke(
        {
            "messages": [
                HumanMessage(content=request.message)
            ],
            "search_query": "",
            "context": "",
            "source": []
        },
        config=config
    )

    return {
        "answer": result["messages"][-1].content
    }


@app.post("/stream-chat")
async def stream_chat(request: ChatRequest):
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
                "search_query": "",
                "context": ""
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