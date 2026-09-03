from contextlib import nullcontext
from pathlib import Path
from typing import Annotated, Literal, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, SystemMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages

from app.journal_lookup import (
    format_scholarly_references,
    is_journal_lookup_request,
    lookup_related_scholarly_references,
)
from app.llm import llm
from app.observability import get_langfuse_client, update_observation
from app.vector_store import create_retriever, load_vector_store

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
    langfuse = get_langfuse_client()
    observation = (
        langfuse.start_as_current_observation(
            as_type="tool",
            name="lookup-journal-references",
            input={
                "query": latest_content,
            },
        )
        if langfuse is not None
        else nullcontext()
    )

    with observation as span:
        try:
            references = lookup_related_scholarly_references(
                latest_content
            )
            answer = format_scholarly_references(references)
            update_observation(
                span,
                output={
                    "reference_count": len(references),
                    "sources": [
                        reference.get("source")
                        for reference in references
                    ],
                },
            )
        except Exception:
            update_observation(
                span,
                level="ERROR",
                status_message="Failed to look up scholarly references.",
            )
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


def rewrite_query(state: RAGState):
    messages = state["messages"]

    system_message = SystemMessage(
        content="""
Rewrite the user's latest question into a standalone search query.

Use the conversation history to resolve references such as:
"it", "that", "they", "this method", etc.

return only the rewritten query.
Do not answer the question
"""
    )

    response = llm.invoke(
        [
            system_message,
            *messages
        ],
        config={
            "run_name": "rewrite-query"
        },
    )

    return {
        "search_query": response.content
    }


def retrieve(state: RAGState):
    langfuse = get_langfuse_client()
    observation = (
        langfuse.start_as_current_observation(
            as_type="span",
            name="prepare-retrieved-context",
            input={
                "query": state["search_query"],
                "document_id": state["document_id"],
            },
        )
        if langfuse is not None
        else nullcontext()
    )

    with observation as span:
        retriever = create_retriever(
            vector_store,
            state["document_id"]
        )

        documents = retriever.invoke(
            state["search_query"],
            config={
                "run_name": "retrieve-context"
            },
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

        update_observation(
            span,
            output={
                "chunk_count": len(documents),
                "sources": sources,
            },
        )

        return {
            "context": context,
            "sources": sources
        }


def generate(state: RAGState):
    source_lines = "\n".join(
        f"- {source['source']}, page {source['page']}"
        for source in state.get("sources", [])
    )

    if not source_lines:
        source_lines = "- No retrieved sources available"

    system_message = SystemMessage(
        content=f"""
You are an assistant that answers questions using retrieved context from an uploaded document.

Important rules:
- The user's full PDF may have been uploaded and processed.
- You only receive the retrieved chunks below, not the whole document at once.
- Do not say the user only uploaded an excerpt.
- Do not say the full document was not uploaded.
- Answer only from the retrieved context.
- If the retrieved context is not enough to answer, say the answer was not found in the retrieved context.
- Do not add inline source citations after every sentence.
- Do not write a "Sources" section in the answer text. The interface will display sources separately.

Retrieved context:
{state["context"]}

Retrieved sources:
{source_lines}

Answer clearly and concisely. If you don't know the answer, just says so
"""
    )

    messages = [
        system_message,
        *state["messages"]
    ]

    response = llm.invoke(
        messages,
        config={
            "run_name": "generate-response"
        },
    )

    return {
        "messages": [response]
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
graph_builder.add_edge("generate", END)

memory = InMemorySaver()

rag_graph = graph_builder.compile(
    checkpointer=memory
)
