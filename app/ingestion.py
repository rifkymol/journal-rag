from app.document_loader import load_pdf
from app.text_splitter import split_documents
from app.vector_store import create_vector_store


def ingest_pdf(file_path: str):
    documents = load_pdf(file_path)

    chunks = split_documents(documents)

    create_vector_store(chunks)

    return {
        "pages": len(documents),
        "chunks": len(chunks)
    }

