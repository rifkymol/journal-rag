from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from dotenv import load_dotenv

load_dotenv()

embeddings = OpenAIEmbeddings(
    model="text-embedding-3-small"
)

CHROMA_PATH = "data/chroma"

# Vector Store = tempat + kemampuan search
# Retriever = interface/komponen pencarian

# ini untuk ingestion - PDF -> Load -> Chunk -> Embed -> Save Chroma
def create_vector_store(chunks):
    vector_store = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=CHROMA_PATH
    )

    return vector_store

# untuk menggunakan database yang sudah ada
# Query - Question -> Retrieve dari Chroma -> Context -> LLM
def load_vector_store():
    vectore_store = Chroma(
        persist_directory=CHROMA_PATH,
        embedding_function=embeddings
    )

    return vectore_store

def create_retriever(vector_store, document_ids: str | list[str]):
    if isinstance(document_ids, str):
        document_ids = [document_ids]

    document_filter = (
        {"document_id": document_ids[0]}
        if len(document_ids) == 1
        else {"document_id": {"$in": document_ids}}
    )
    retriever = vector_store.as_retriever(
        search_kwargs={
            "k": 8,
            "filter": document_filter,
        }
    )

    return retriever

def delete_document(document_id: str):
    vector_store = load_vector_store()
    
    result = vector_store.get(
        where={
            "document_id": document_id
        }
    )

    ids = result["ids"]

    if ids:
        vector_store.delete(
            ids=ids
        )
