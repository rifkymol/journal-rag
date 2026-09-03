from contextlib import nullcontext

from langchain_core.messages import AIMessage, HumanMessage

from app.observability import (
    create_langfuse_handler,
    get_langfuse_client,
    propagate_chat_attributes,
    update_observation,
)
from app.rag_graph import rag_graph


FINAL_MESSAGE_NODES = {
    "lookup_journal_references",
    "missing_document",
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
    document_id: str | None,
    session_id: str,
):
    langfuse = get_langfuse_client()
    answer_chunks: list[str] = []
    sources: list[dict] = []

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
            "document_id": document_id,
        },
        "run_name": "run-chat-graph",
    }

    root_observation = (
        langfuse.start_as_current_observation(
            as_type="span",
            name="chat-response",
            input={
                "message": message,
                "document_id": document_id,
            },
        )
        if langfuse is not None
        else nullcontext()
    )

    with root_observation as root_span:
        with propagate_chat_attributes(session_id, document_id):
            langfuse_handler = create_langfuse_handler()

            if langfuse_handler is not None:
                config["callbacks"] = [langfuse_handler]

            async for event in rag_graph.astream_events(
                {
                    "messages": [
                        HumanMessage(
                            content=message
                        )
                    ],
                    "document_id": document_id,
                    "request_route": "rag",
                    "search_query": "",
                    "context": "",
                    "sources": []
                },
                config=config,
                version="v2"
            ):
                metadata = event.get("metadata") or {}
                node_name = metadata.get("langgraph_node")

                if event["event"] == "on_chain_end" and node_name == "retrieve":
                    retrieve_output = event["data"].get("output", {})
                    sources = retrieve_output.get("sources", [])

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
                },
            )

    yield {
        "event": "done",
        "data": "[DONE]"
    }
