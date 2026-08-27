from uuid import uuid4

from app.document_loader import load_pdf
from app.text_splitter import split_documents
from app.vector_store import create_vector_store


def ingest_pdf(file_path: str):
    document_id = str(uuid4())

    documents = load_pdf(file_path)

    for document in documents:
        document.metadata["document_id"] = document_id

    chunks = split_documents(documents)

    create_vector_store(chunks)

    return {
        "document_id": document_id,
        "pages": len(documents),
        "chunks": len(chunks)
    }

