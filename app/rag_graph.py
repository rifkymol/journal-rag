from typing import Annotated, TypedDict
from pathlib import Path

from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import InMemorySaver
from langchain_core.messages import (
    BaseMessage,
    SystemMessage,
)


from app.llm import llm
from app.vector_store import (
    load_vector_store,
    create_retriever
)


class RAGState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    document_id: str
    search_query: str
    context: str
    source: list[dict]


vector_store = load_vector_store()
retriever = create_retriever(vector_store)


def retrieve(state: RAGState):
    retriever = create_retriever(
        vector_store,
        state["document_id"]
    )

    documents = retriever.invoke(
        state["search_query"]
    )

    context = "\n\n".join(
        document.page_content
        for document in documents
    )

    sources = [
        {
            "source": Path(
                document.metadata.get("source", "")
            ).name,
            "page": document.metadata.get("page", 0) + 1
        }
        for document in documents
    ]

    return {
        "context": context,
        "sources": sources
    }

def generate(state: RAGState):
    system_message = SystemMessage(
        content=f"""
You are an assistant that answers question based only on the provided journal context.

Answer based only on the provided journal context.
Journal context:
{state["context"]}

Answer Clearly and concisely
if you don't find the answer, just say so
""")

    messages = [
        system_message,
        *state["messages"]
    ]

    response = llm.invoke(messages)

    return {
        "messages": [response]
    }

def rewrite_query(state: RAGState):
    messages = state["messages"]

    system_message = SystemMessage(
        content=f"""

Rewrite the user's latest question into a standalone search query.

Use the conversation history to resolve references such as:
"it", "that", "they", "this method", etc.

return only the rewritten query.
Do not answer the question
"""
    )

    response = llm.invoke([
        system_message,
        *messages
    ])

    return {
        "search_query": response.content
    }

graph_builder = StateGraph(RAGState)

graph_builder.add_node("rewrite_query", rewrite_query)
graph_builder.add_node("retrieve", retrieve)
graph_builder.add_node("generate", generate)

graph_builder.add_edge(START, "rewrite_query")
graph_builder.add_edge("rewrite_query", "retrieve")
graph_builder.add_edge("retrieve", "generate")
graph_builder.add_edge("generate",END)

memory = InMemorySaver()

rag_graph = graph_builder.compile(
    checkpointer=memory
)
