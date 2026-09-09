import unittest
from unittest.mock import patch

from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from langchain_core.messages import HumanMessage

from app.main import app
from app.models import ChatRequest, SourceTextRequest
from app.rag_graph import route_request
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
        route = route_request({
            "messages": [HumanMessage(content="Make flashcards")],
            "document_ids": ["source-1"],
            "mode": "flashcards",
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


if __name__ == "__main__":
    unittest.main()
