from contextlib import nullcontext
import json

from langchain_core.messages import AIMessage, HumanMessage

from app.observability import (
    create_langfuse_handler,
    get_langfuse_client,
    propagate_chat_attributes,
    update_observation,
)
from app.rag_graph import rag_graph
from app.source_utils import compact_sources


FINAL_MESSAGE_NODES = {
    "lookup_journal_references",
    "missing_document",
    "study_artifact",
}


def get_message_content(output: dict) -> str:
    messages = output.get("messages", [])

    if not messages:
        return ""

    latest_message = messages[-1]

    if isinstance(latest_message, AIMessage):
        return str(latest_message.content)

    content = getattr(latest_message, "content", "")
    return str(content)


async def stream_chat_response(
    message: str,
    thread_id: str,
    document_ids: list[str] | str,
    session_id: str,
    mode: str = "auto",
    language: str = "auto",
):
import asyncio

try:
    async for event in _stream_chat_response(
        message,
        thread_id,
        document_ids,
        session_id,
        mode,
        language,
    ):
        yield event
except asyncio.CancelledError:
    raise
except Exception:
    yield {
        "event": "error",
        "data": "The study assistant could not complete this request.",
    }
    yield {
        "event": "done",
        "data": "[DONE]",
    }


async def _stream_chat_response(
    message: str,
    thread_id: str,
    document_ids: list[str] | str,
    session_id: str,
    mode: str = "auto",
    language: str = "auto",
):
    if isinstance(document_ids, str):
        document_ids = [document_ids] if document_ids else []

    langfuse = get_langfuse_client()
    answer_chunks: list[str] = []
    sources: list[dict] = []
    artifact: dict | None = None

    config = {
        "configurable": {
            "thread_id": thread_id
        },
        "metadata": {
            "langfuse_session_id": session_id,
            "langfuse_tags": [
                "journal-rag",
                "chat",
                "langgraph",
            ],
            "endpoint": "/chat",
            "document_ids": document_ids,
            "mode": mode,
            "language": language,
        },
        "run_name": "run-chat-graph",
    }

    root_observation = (
        langfuse.start_as_current_observation(
            as_type="span",
            name="chat-response",
            input={
                "message": message,
                "document_ids": document_ids,
            },
        )
        if langfuse is not None
        else nullcontext()
    )

    with root_observation as root_span:
        with propagate_chat_attributes(
            session_id,
            document_ids[0] if document_ids else None,
        ):
            langfuse_handler = create_langfuse_handler()

            if langfuse_handler is not None:
                config["callbacks"] = [langfuse_handler]

            yield {
                "event": "status",
                "data": "Thinking through your sources...",
            }

            async for event in rag_graph.astream_events(
                {
                    "messages": [
                        HumanMessage(
                            content=message
                        )
                    ],
                    "document_ids": document_ids,
                    "mode": mode,
                    "language": language,
                    "request_route": "rag",
                    "search_query": "",
                    "context": "",
                    "sources": [],
                    "artifact": None,
                },
                config=config,
                version="v2"
            ):
                metadata = event.get("metadata") or {}
                node_name = metadata.get("langgraph_node")

                if event["event"] == "on_chain_end" and node_name == "retrieve":
                    retrieve_output = event["data"].get("output", {})
                    sources = retrieve_output.get("sources", [])

                if event["event"] == "on_chain_end" and node_name == "study_artifact":
                    artifact = event["data"].get("output", {}).get("artifact")

                if (
                    event["event"] == "on_chat_model_stream"
                    and node_name == "generate"
                ):
                    chunk = event["data"]["chunk"]

                    if chunk.content:
                        answer_chunks.append(str(chunk.content))
                        yield {
                            "event": "message",
                            "data": chunk.content
                        }

                if (
                    event["event"] == "on_chain_end"
                    and node_name in FINAL_MESSAGE_NODES
                ):
                    content = get_message_content(event["data"].get("output", {}))

                    if content:
                        answer_chunks.append(content)
                        yield {
                            "event": "message",
                            "data": content
                        }

            update_observation(
                root_span,
                output={
                    "answer": "".join(answer_chunks),
                    "sources": sources,
                    "artifact_type": artifact.get("type") if artifact else None,
                },
            )

    compacted_sources = compact_sources(sources)

    if compacted_sources:
        yield {
            "event": "sources",
            "data": json.dumps(compacted_sources)
        }

    if artifact:
        yield {
            "event": "artifact",
            "data": json.dumps(artifact),
        }

    yield {
        "event": "done",
        "data": "[DONE]"
    }
