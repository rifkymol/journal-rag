from datetime import datetime, timezone
from typing import Any

from app.journal_store import (
    add_journal,
    delete_journal_record,
    get_journal_by_session,
    get_journals_by_session,
)
from app.models import SourceRecord


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_source(record: dict[str, Any]) -> dict[str, Any]:
    document_id = str(record.get("document_id") or record.get("source_id") or "")
    source = {
        **record,
        "source_id": document_id,
        "document_id": document_id,
        "source_type": record.get("source_type", "pdf"),
        "title": record.get("title") or record.get("filename") or "Untitled source",
        "created_at": record.get("created_at") or utc_now(),
    }
    return {**record, **SourceRecord.model_validate(source).model_dump()}


def add_source(record: dict[str, Any]) -> dict[str, Any]:
    normalized = normalize_source(record)
    add_journal(normalized)
    return normalized


def list_sources(session_id: str) -> list[dict[str, Any]]:
    return [normalize_source(record) for record in get_journals_by_session(session_id)]


def get_source(source_id: str, session_id: str) -> dict[str, Any] | None:
    record = get_journal_by_session(source_id, session_id)
    return normalize_source(record) if record else None


def delete_source(source_id: str, session_id: str) -> None:
    delete_journal_record(source_id, session_id)
