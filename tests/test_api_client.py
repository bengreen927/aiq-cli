"""Tests for AIQ API client."""
from unittest.mock import MagicMock, patch

import pytest

from aiq.api.client import AIQClient, EvaluationStatus
from aiq.extractor.models import MacfDocument, MacfEntry


def _make_doc() -> MacfDocument:
    return MacfDocument(
        domain_knowledge=[
            MacfEntry(
                source="skill:testing",
                entry_type="coding_standard",
                content="Always write tests first.",
                category="engineering",
            ),
        ],
        workflow_patterns=[],
        tool_integrations=[],
    )


def test_submit_evaluation_sends_correct_payload() -> None:
    """Client should POST MACF config with entry_type mapped to type."""
    client = AIQClient(base_url="http://localhost:8000", token="test-token")
    mock_response = MagicMock()
    mock_response.status_code = 202
    mock_response.json.return_value = {
        "evaluation_id": "eval-123",
        "status": "pending",
        "message": "Queued",
    }
    mock_response.raise_for_status = MagicMock()

    with patch("aiq.api.client.httpx.post", return_value=mock_response) as mock_post:
        result = client.submit_evaluation(config=_make_doc(), role_category="engineering")

    assert result == "eval-123"
    call_args = mock_post.call_args
    payload = call_args[1]["json"]
    entry = payload["config"]["domain_knowledge"][0]
    assert "type" in entry
    assert "entry_type" not in entry
    assert entry["type"] == "coding_standard"


def test_poll_status_returns_status() -> None:
    """Client should return evaluation status from GET endpoint."""
    client = AIQClient(base_url="http://localhost:8000", token="test-token")
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "evaluation_id": "eval-123",
        "status": "completed",
        "role_category": "engineering",
        "result": {"aggregate_score": 72.5},
    }
    mock_response.raise_for_status = MagicMock()

    with patch("aiq.api.client.httpx.get", return_value=mock_response):
        status = client.get_status("eval-123")

    assert status.status == "completed"
    assert status.result["aggregate_score"] == 72.5


def test_submit_raises_on_auth_error() -> None:
    """Client should raise on 401."""
    client = AIQClient(base_url="http://localhost:8000", token="bad-token")
    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.raise_for_status.side_effect = Exception("Unauthorized")

    with patch("aiq.api.client.httpx.post", return_value=mock_response):
        with pytest.raises(Exception, match="Unauthorized"):
            client.submit_evaluation(_make_doc(), "engineering")
