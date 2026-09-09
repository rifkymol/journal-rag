from uuid import uuid4

from langchain_core.documents import Document

from app.document_loader import load_pdf
from app.text_splitter import split_documents
from app.vector_store import create_vector_store


def ingest_pdf(
        file_path: str,
        session_id: str
    ):

    document_id = str(uuid4())

    documents = load_pdf(file_path)

    for document in documents:
        document.metadata["document_id"] = document_id
        document.metadata["session_id"] = session_id
        document.metadata["source_type"] = "pdf"

    chunks = split_documents(documents)

    create_vector_store(chunks)

    return {
        "document_id": document_id,
        "pages": len(documents),
        "chunks": len(chunks)
    }


def ingest_text(
        text: str,
        title: str,
        session_id: str,
        language: str = "auto",
    ):
    document_id = str(uuid4())
    document = Document(
        page_content=text,
        metadata={
            "document_id": document_id,
            "session_id": session_id,
            "source": title,
            "title": title,
            "source_type": "text",
            "language": language,
            "page": 0,
        },
    )
    chunks = split_documents([document])
    create_vector_store(chunks)

    return {
        "document_id": document_id,
        "pages": 1,
        "chunks": len(chunks),
    }

