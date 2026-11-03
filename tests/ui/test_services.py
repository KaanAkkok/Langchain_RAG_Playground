import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from lang_rag_playground.graphs.graph import agentic_graph
from lang_rag_playground.ui.services import (
    build_app_services,
)


def test_agentic_graph_allows_none_store_and_checkpointer():
    with (
        patch(
            "lang_rag_playground.graphs.graph.build_intent_chain",
            return_value=MagicMock(),
        ),
        patch(
            "lang_rag_playground.graphs.graph.build_reranker_chain",
            return_value=MagicMock(),
        ),
        patch(
            "lang_rag_playground.graphs.graph.build_assistant_agent",
            return_value=MagicMock(),
        ),
        patch(
            "lang_rag_playground.graphs.graph.build_judge_chain",
            return_value=MagicMock(),
        ),
        patch(
            "lang_rag_playground.graphs.graph.build_memory_extract_chain",
            return_value=MagicMock(),
        ),
    ):
        compiled = agentic_graph(
            retrieval_service=MagicMock(),
            guardrails_service=MagicMock(),
            store=None,
            checkpointer=None,
        )
        assert compiled is not None


def test_build_app_services_raises_clear_error_when_api_key_missing(monkeypatch):
    from pydantic import SecretStr

    from lang_rag_playground.core.settings import settings

    monkeypatch.setattr(settings, "GEMINI_API_KEY", SecretStr(""))
    with pytest.raises(RuntimeError, match="GEMINI_API_KEY"):
        build_app_services()


def test_build_app_services_raises_clear_error_when_qdrant_unreachable(monkeypatch):
    from pydantic import SecretStr

    from lang_rag_playground.core.settings import settings

    monkeypatch.setattr(settings, "GEMINI_API_KEY", SecretStr("test-key"))
    monkeypatch.setattr(
        settings, "GEMINI_EMBEDDING_MODEL", "models/gemini-embedding-001"
    )
    monkeypatch.setattr(settings, "GEMINI_INTENT_MODEL", "gemini-2.5-flash")
    monkeypatch.setattr(settings, "GEMINI_RERANKER_MODEL", "gemini-2.5-flash")
    monkeypatch.setattr(settings, "GEMINI_ASSISTANT_MODEL", "gemini-2.5-flash")
    monkeypatch.setattr(settings, "GEMINI_JUDGE_MODEL", "gemini-2.5-flash")
    monkeypatch.setattr(settings, "GEMINI_MEMORY_MODEL", "gemini-2.5-flash")

    fake_vectordb = MagicMock()
    fake_vectordb.client.get_collections.side_effect = ConnectionError("refused")

    with (
        patch(
            "lang_rag_playground.ui.services.build_embedding_model",
            return_value=MagicMock(),
        ),
        patch(
            "lang_rag_playground.ui.services.AsyncQdrantVectorDBService",
            return_value=fake_vectordb,
        ),
        pytest.raises(RuntimeError, match="Qdrant"),
    ):
        build_app_services()

