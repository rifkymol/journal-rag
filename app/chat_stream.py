from langchain_core.messages import AIMessage, HumanMessage

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


async def stream_chat_response(message: str, thread_id: str, document_id: str | None):
    config = {
        "configurable": {
            "thread_id": thread_id
        }
    }

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

        if (
            event["event"] == "on_chat_model_stream"
            and node_name == "generate"
        ):
            chunk = event["data"]["chunk"]

            if chunk.content:
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
                yield {
                    "event": "message",
                    "data": content
                }

    yield {
        "event": "done",
        "data": "[DONE]"
    }
