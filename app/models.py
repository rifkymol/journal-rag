from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


ChatMode = Literal[
    "auto",
    "explain",
    "summarize",
    "compare",
    "quiz",
    "flashcards",
    "citations",
    "web_references",
]
Language = Literal["auto", "en", "id"]
SourceType = Literal["pdf", "text"]
ArtifactType = Literal["summary", "comparison", "quiz", "flashcards", "citations"]


class SourceRecord(BaseModel):
    source_id: str
    document_id: str
    session_id: str
    source_type: SourceType
    title: str
    filename: str | None = None
    pages: int = 0
    chunks: int = 0
    language: str | None = None
    created_at: str


class SourceTextRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    text: str = Field(min_length=1, max_length=200_000)
    language: Language = "auto"

    @field_validator("title", "text")
    @classmethod
    def strip_value(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Value cannot be empty")
        return value


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=20_000)
    thread_id: str = Field(min_length=1, max_length=200)
    document_id: str | None = None
    document_ids: list[str] = Field(default_factory=list, max_length=10)
    mode: ChatMode = "auto"
    language: Language = "auto"

    @field_validator("message", "thread_id")
    @classmethod
    def strip_required_value(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Value cannot be empty")
        return value

    @field_validator("document_ids")
    @classmethod
    def normalize_document_ids(cls, values: list[str]) -> list[str]:
        return list(dict.fromkeys(value.strip() for value in values if value.strip()))

    @model_validator(mode="after")
    def merge_legacy_document_id(self):
        if self.document_id and self.document_id not in self.document_ids:
            self.document_ids.insert(0, self.document_id)
        if self.document_ids and not self.document_id:
            self.document_id = self.document_ids[0]
        return self


class SourceReference(BaseModel):
    source: str
    pages: list[int] = Field(default_factory=list)
    page_label: str = ""
    source_id: str | None = None
    snippet: str | None = None


class StudyArtifact(BaseModel):
    type: ArtifactType
    title: str
    data: dict[str, Any]
