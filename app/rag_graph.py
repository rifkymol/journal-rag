from typing import Annotated, Literal, TypedDict
from pathlib import Path

from langchain_core.messages import AIMessage, BaseMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import InMemorySaver
from langchain_core.messages import (
    SystemMessage,
)


from app.llm import llm
from app.vector_store import (
    load_vector_store,
    create_retriever
)
from app.journal_lookup import (
    format_scholarly_references,
    is_journal_lookup_request,
    lookup_related_scholarly_references,
)

RequestRoute = Literal[
    "journal_lookup",
    "rag",
    "missing_document",
]

class RAGState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    document_id: str | None
    request_route: RequestRoute
    search_query: str
    context: str
    sources: list[dict]


vector_store = load_vector_store()


def route_request(state: RAGState):
    latest_message = state["messages"][-1]
    latest_content = str(latest_message.content)

    if is_journal_lookup_request(latest_content):
        return {
            "request_route": "journal_lookup"
        }

    if state.get("document_id") is None:
        return {
            "request_route": "missing_document"
        }

    return {
        "request_route": "rag"
    }


def select_route(state: RAGState):
    return state["request_route"]


def missing_document(state: RAGState):
    return {
        "messages": [
            AIMessage(
                content="Please select or upload a journal before asking about its content."
            )
        ]
    }


def lookup_journal_references(state: RAGState):
    latest_message = state["messages"][-1]
    latest_content = str(latest_message.content)

    try:
        references = lookup_related_scholarly_references(
            latest_content
        )
        answer = format_scholarly_references(references)
    except Exception:
        answer = (
            "I could not look up related scholarly references. "
            "Please check to the Administrator."
        )

    return {
        "messages": [
            AIMessage(
                content=answer
            )
        ]
    }


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

graph_builder.add_node("route_request", route_request)
graph_builder.add_node("missing_document", missing_document)
graph_builder.add_node("lookup_journal_references", lookup_journal_references)
graph_builder.add_node("rewrite_query", rewrite_query)
graph_builder.add_node("retrieve", retrieve)
graph_builder.add_node("generate", generate)

graph_builder.add_edge(START, "route_request")
graph_builder.add_conditional_edges(
    "route_request",
    select_route,
    {
        "journal_lookup": "lookup_journal_references",
        "rag": "rewrite_query",
        "missing_document": "missing_document",
    }
)
graph_builder.add_edge("lookup_journal_references", END)
graph_builder.add_edge("missing_document", END)
graph_builder.add_edge("rewrite_query", "retrieve")
graph_builder.add_edge("retrieve", "generate")
graph_builder.add_edge("generate",END)

memory = InMemorySaver()

rag_graph = graph_builder.compile(
    checkpointer=memory
)
