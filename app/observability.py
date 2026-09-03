import os
from contextlib import nullcontext
from typing import Any

from dotenv import load_dotenv

load_dotenv()

from langfuse import get_client, propagate_attributes
from langfuse.langchain import CallbackHandler


LANGFUSE_REQUIRED_ENV = (
    "LANGFUSE_PUBLIC_KEY",
    "LANGFUSE_SECRET_KEY",
)


def is_langfuse_configured() -> bool:
    has_keys = all(os.getenv(key) for key in LANGFUSE_REQUIRED_ENV)
    has_host = bool(os.getenv("LANGFUSE_BASE_URL") or os.getenv("LANGFUSE_HOST"))

    return has_keys and has_host


def get_langfuse_client():
    if not is_langfuse_configured():
        return None

    return get_client()


def create_langfuse_handler():
    if not is_langfuse_configured():
        return None

    return CallbackHandler()


def propagate_chat_attributes(
    session_id: str,
    document_id: str | None,
):
    if not is_langfuse_configured():
        return nullcontext()

    return propagate_attributes(
        trace_name="chat-response",
        session_id=session_id,
        tags=[
            "journal-rag",
            "chat",
            "langgraph",
        ],
        metadata={
            "endpoint": "/chat",
            "document_id": document_id,
            "has_document": document_id is not None,
        },
    )


def update_observation(observation: Any, **kwargs: Any) -> None:
    if observation is None:
        return

    observation.update(**kwargs)


def flush_langfuse() -> None:
    langfuse = get_langfuse_client()
    if langfuse is not None:
        langfuse.flush()
