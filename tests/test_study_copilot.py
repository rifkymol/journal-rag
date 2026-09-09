import unittest
from contextlib import nullcontext
from unittest.mock import MagicMock, patch

from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, HumanMessage

from app.main import app
from app.chat_stream import (
    get_artifact,
    get_message_content,
    get_retrieve_sources,
    stream_chat_response,
)
from app.models import ChatRequest, SourceTextRequest, StudyArtifact
from app.rag_graph import generate_study_artifact, route_request
from app.source_store import normalize_source
from app.source_utils import compact_sources


class StudyCopilotContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_legacy_document_id_is_normalized_for_chat(self):
        request = ChatRequest(
            message="Explain the method",
            thread_id="thread-1",
            document_id="source-1",
        )

        self.assertEqual(request.document_ids, ["source-1"])

    def test_duplicate_document_ids_are_removed(self):
        request = ChatRequest(
            message="Compare these papers",
            thread_id="thread-1",
            document_ids=["source-1", "source-1", "source-2"],
            mode="compare",
        )

        self.assertEqual(request.document_ids, ["source-1", "source-2"])

    def test_text_source_contract_rejects_blank_content(self):
        with self.assertRaises(ValueError):
            SourceTextRequest(title="Notes", text="   ")

    def test_route_uses_study_artifact_for_explicit_modes(self):
        for mode in ("summarize", "compare", "quiz", "flashcards", "citations"):
            route = route_request({
                "messages": [HumanMessage(content="Study this source")],
                "document_ids": ["source-1"],
                "mode": mode,
            })

            self.assertEqual(route["request_route"], "study_artifact")

    def test_route_requires_a_source_for_document_modes(self):
        route = route_request({
            "messages": [HumanMessage(content="Explain this")],
            "document_ids": [],
            "mode": "explain",
        })

        self.assertEqual(route["request_route"], "missing_document")

    def test_sources_are_grouped_by_source_and_page(self):
        sources = compact_sources([
            {"source": "paper.pdf", "source_id": "one", "page": 1},
            {"source": "paper.pdf", "source_id": "one", "page": 2},
            {"source": "paper.pdf", "source_id": "two", "page": 1},
        ])

        self.assertEqual(len(sources), 2)
        self.assertEqual(sources[0]["page_label"], "1-2")

    def test_retrieve_event_parser_ignores_non_mapping_output(self):
        event = {"data": {"output": "retrieved text"}}

        self.assertEqual(get_retrieve_sources(event), [])

    def test_retrieve_event_parser_extracts_sources_from_mapping_output(self):
        sources = [{"source": "paper.pdf", "page": 1}]
        event = {"data": {"output": {"sources": sources}}}

        self.assertEqual(get_retrieve_sources(event), sources)

    def test_artifact_and_message_parsers_ignore_string_outputs(self):
        event = {"data": {"output": "intermediate output"}}

        self.assertIsNone(get_artifact(event))
        self.assertEqual(get_message_content("intermediate output"), "")

    def test_artifact_and_message_parsers_extract_mapping_outputs(self):
        event = {
            "data": {
                "output": {
                    "artifact": {
                        "type": "summary",
                        "title": "Research brief",
                        "data": {"findings": []},
                    },
                    "messages": [HumanMessage(content="Research brief")],
                }
            }
        }

        self.assertEqual(get_artifact(event)["title"], "Research brief")
        self.assertEqual(get_message_content(event["data"]["output"]), "Research brief")

    def test_study_artifact_uses_function_calling_output(self):
        response = StudyArtifact(
            type="summary",
            title="Research brief",
            data={"findings": []},
        )
        structured_llm = MagicMock()
        structured_llm.invoke.return_value = response

        with patch("app.rag_graph.llm") as mocked_llm:
            mocked_llm.with_structured_output.return_value = structured_llm
            result = generate_study_artifact({
                "messages": [HumanMessage(content="Summarize this")],
                "mode": "summarize",
                "language": "en",
                "context": "A grounded context.",
            })

        mocked_llm.with_structured_output.assert_called_once_with(
            StudyArtifact,
            method="function_calling",
        )
        self.assertEqual(result["artifact"], response.model_dump())

    def test_legacy_source_records_receive_generic_metadata(self):
        source = normalize_source({
            "document_id": "source-1",
            "session_id": "session-1",
            "filename": "paper.pdf",
            "pages": 4,
            "chunks": 8,
        })

        self.assertEqual(source["source_id"], "source-1")
        self.assertEqual(source["source_type"], "pdf")
        self.assertEqual(source["title"], "paper.pdf")

    def test_new_routes_are_registered(self):
        paths = {
            route.path
            for route in app.routes
            if isinstance(route, APIRoute)
        }

        self.assertIn("/sources", paths)
        self.assertIn("/sources/text", paths)
        self.assertIn("/sources/{source_id}/preview", paths)

    def test_text_source_route_keeps_session_header_and_contract(self):
        with patch(
            "app.main.create_text_source",
            return_value={
                "source_id": "source-1",
                "document_id": "source-1",
                "source_type": "text",
                "title": "Notes",
            },
        ):
            response = self.client.post(
                "/sources/text",
                headers={"X-Session-ID": "session-1"},
                json={"title": "Notes", "text": "Important concept"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["source_type"], "text")

    def test_chat_rejects_a_source_from_another_session(self):
        response = self.client.post(
            "/chat",
            headers={"X-Session-ID": "session-1"},
            json={
                "message": "Explain this",
                "thread_id": "thread-1",
                "document_ids": ["not-owned"],
            },
        )

        self.assertEqual(response.status_code, 404)


class StudyCopilotStreamTests(unittest.IsolatedAsyncioTestCase):
    async def test_study_artifact_stream_ignores_intermediate_string_events(self):
        artifact = {
            "type": "summary",
            "title": "Research brief",
            "data": {"findings": []},
        }

        class FakeGraph:
            async def astream_events(self, *_args, **_kwargs):
                yield {
                    "event": "on_chain_end",
                    "metadata": {"langgraph_node": "study_artifact"},
                    "data": {"output": "intermediate output"},
                }
                yield {
                    "event": "on_chain_end",
                    "metadata": {"langgraph_node": "study_artifact"},
                    "data": {
                        "output": {
                            "artifact": artifact,
                            "messages": [AIMessage(content="Research brief")],
                        }
                    },
                }

        with (
            patch("app.chat_stream.rag_graph", FakeGraph()),
            patch("app.chat_stream.get_langfuse_client", return_value=None),
            patch("app.chat_stream.create_langfuse_handler", return_value=None),
            patch("app.chat_stream.propagate_chat_attributes", return_value=nullcontext()),
        ):
            events = [
                event
                async for event in stream_chat_response(
                    "Summarize this",
                    "thread-1",
                    ["source-1"],
                    "session-1",
                    "summarize",
                    "en",
                )
            ]

        self.assertEqual(
            [event["event"] for event in events],
            ["status", "message", "artifact", "done"],
        )
        self.assertEqual(events[-1]["data"], "[DONE]")

    async def test_stream_errors_end_with_error_then_done(self):
        async def failing_stream(*_args, **_kwargs):
            raise RuntimeError("structured output failed")
            yield  # pragma: no cover

        with patch("app.chat_stream._stream_chat_response", failing_stream):
            events = [
                event
                async for event in stream_chat_response(
                    "Summarize this",
                    "thread-1",
                    ["source-1"],
                    "session-1",
                    "summarize",
                    "en",
                )
            ]

        self.assertEqual([event["event"] for event in events], ["error", "done"])


if __name__ == "__main__":
    unittest.main()
