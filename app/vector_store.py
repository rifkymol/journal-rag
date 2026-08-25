from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma

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

def create_retriever(vector_store):
    retriever = vector_store.as_retriever(
        search_kwargs={
            "k": 3
        }
    )

    return retriever