import json
import pytest
from unittest.mock import MagicMock, patch
from core.db_connector.ai_service import AIDocumentationService

TABLE_DESC = {
    "instance_name": "db.host.local",
    "schema_name": "mydb",
    "table_name": "users",
    "columns": [{"name": "id", "data_type": "int"}, {"name": "email", "data_type": "varchar"}],
    "primary_key": {"column_names": ["id"]},
    "foreign_keys": [],
}

AI_RESPONSE = {
    "summary": "Stores user accounts.",
    "column_descriptions": {"id": "Primary key", "email": "User email address"},
}


class TestAIDocumentationServiceInit:
    def test_default_model_from_env(self, monkeypatch):
        monkeypatch.setenv("LITELLM_MODEL", "claude-3-haiku")
        svc = AIDocumentationService()
        assert svc.model_name == "claude-3-haiku"

    def test_default_model_fallback(self, monkeypatch):
        monkeypatch.delenv("LITELLM_MODEL", raising=False)
        svc = AIDocumentationService()
        assert svc.model_name == "gpt-4o-mini"

    def test_explicit_model_overrides_env(self, monkeypatch):
        monkeypatch.setenv("LITELLM_MODEL", "ignored")
        svc = AIDocumentationService(model_name="my-model")
        assert svc.model_name == "my-model"


class TestAIDocumentationServiceGenerate:
    def _make_mock_response(self, content: dict):
        mock_msg = MagicMock()
        mock_msg.content = json.dumps(content)
        mock_choice = MagicMock()
        mock_choice.message = mock_msg
        mock_resp = MagicMock()
        mock_resp.choices = [mock_choice]
        return mock_resp

    def test_returns_documentation_on_success(self):
        svc = AIDocumentationService()
        mock_resp = self._make_mock_response(AI_RESPONSE)

        with patch.dict("sys.modules", {"litellm": MagicMock(completion=MagicMock(return_value=mock_resp))}):
            result = svc.generate_table_documentation(TABLE_DESC)

        assert result is not None
        assert result["summary"] == "Stores user accounts."
        assert result["column_descriptions"]["id"] == "Primary key"
        assert "generated_at" in result
        assert result["model"] == svc.model_name

    def test_returns_none_when_litellm_not_installed(self):
        svc = AIDocumentationService()
        with patch.dict("sys.modules", {"litellm": None}):
            result = svc.generate_table_documentation(TABLE_DESC)
        assert result is None
        assert svc.last_error is not None

    def test_returns_none_on_api_error(self):
        svc = AIDocumentationService()
        mock_litellm = MagicMock()
        mock_litellm.completion.side_effect = RuntimeError("API unavailable")

        with patch.dict("sys.modules", {"litellm": mock_litellm}):
            result = svc.generate_table_documentation(TABLE_DESC)

        assert result is None
        assert "API unavailable" in svc.last_error

    def test_last_error_cleared_on_success(self):
        svc = AIDocumentationService()
        svc.last_error = "previous error"
        mock_resp = self._make_mock_response(AI_RESPONSE)

        with patch.dict("sys.modules", {"litellm": MagicMock(completion=MagicMock(return_value=mock_resp))}):
            result = svc.generate_table_documentation(TABLE_DESC)

        assert result is not None
        assert svc.last_error is None

    def test_passes_api_key_from_env(self, monkeypatch):
        monkeypatch.setenv("LITELLM_API_KEY", "test-key")
        monkeypatch.setenv("LITELLM_API_BASE", "http://custom-base")
        svc = AIDocumentationService()
        mock_resp = self._make_mock_response(AI_RESPONSE)
        mock_completion = MagicMock(return_value=mock_resp)

        with patch.dict("sys.modules", {"litellm": MagicMock(completion=mock_completion)}):
            svc.generate_table_documentation(TABLE_DESC)

        call_kwargs = mock_completion.call_args.kwargs
        assert call_kwargs.get("api_key") == "test-key"
        assert call_kwargs.get("api_base") == "http://custom-base"

    def test_does_not_pass_api_key_when_not_set(self, monkeypatch):
        monkeypatch.delenv("LITELLM_API_KEY", raising=False)
        monkeypatch.delenv("LITELLM_API_BASE", raising=False)
        svc = AIDocumentationService()
        mock_resp = self._make_mock_response(AI_RESPONSE)
        mock_completion = MagicMock(return_value=mock_resp)

        with patch.dict("sys.modules", {"litellm": MagicMock(completion=mock_completion)}):
            svc.generate_table_documentation(TABLE_DESC)

        call_kwargs = mock_completion.call_args.kwargs
        assert "api_key" not in call_kwargs
        assert "api_base" not in call_kwargs
