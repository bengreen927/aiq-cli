"""Tests for AIQ CLI."""

from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from aiq.api.client import EvaluationStatus
from aiq.cli import main


def test_cli_version() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.output


def test_cli_scan() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["scan"])
    assert result.exit_code == 0
    # Should show scan results summary
    assert "Scan" in result.output or "scan" in result.output.lower()


def test_cli_evaluate_not_authenticated() -> None:
    """Evaluate without auth should fail with a clear error."""
    runner = CliRunner()
    result = runner.invoke(main, ["evaluate", "--auto-approve", "--role", "engineering"])
    assert result.exit_code == 1
    assert "not authenticated" in result.output.lower() or "aiq login" in result.output.lower()


def test_cli_evaluate_full_flow() -> None:
    """Full evaluate flow with mocked API calls."""
    mock_token_store = MagicMock()
    mock_token_store.is_authenticated = True
    mock_token_store.load_token.return_value = "fake-token-123"

    mock_client = MagicMock()
    mock_client.submit_evaluation.return_value = "eval-abc-123"
    mock_client.get_status.return_value = EvaluationStatus(
        evaluation_id="eval-abc-123",
        status="completed",
        role_category="engineering",
        result={
            "overall_score": 82,
            "model_scores": {"claude": 85, "gpt": 80, "gemini": 81},
            "layer_scores": {
                "execution": 90,
                "robustness": 75,
                "constraint_satisfaction": 80,
                "ground_truth": 85,
                "telemetry": 78,
                "ai_judge": 84,
            },
            "challenge_version": "v1.0",
        },
        completed_at="2026-03-20T12:00:00Z",
    )

    runner = CliRunner()
    with runner.isolated_filesystem():
        with patch("aiq.cli.TokenStore", return_value=mock_token_store), \
             patch("aiq.cli.AIQClient", return_value=mock_client):
            result = runner.invoke(
                main,
                ["evaluate", "--auto-approve", "--role", "engineering", "-o", "test-report.pdf"],
            )

    assert result.exit_code == 0, f"CLI failed: {result.output}"

    # Verify submission happened
    mock_client.submit_evaluation.assert_called_once()
    call_kwargs = mock_client.submit_evaluation.call_args
    assert call_kwargs.kwargs.get("role_category") == "engineering" or \
        (call_kwargs[1].get("role_category") == "engineering" if len(call_kwargs) > 1 else
         call_kwargs[0][1] == "engineering" if len(call_kwargs[0]) > 1 else False)

    # Verify polling happened
    mock_client.get_status.assert_called_once_with("eval-abc-123")

    # Verify output contains expected content
    assert "eval-abc-123" in result.output
    assert "submitted" in result.output.lower() or "Submitted" in result.output
    assert "complete" in result.output.lower()
    assert "82" in result.output  # overall score


def test_cli_evaluate_poll_until_complete() -> None:
    """Evaluate polls multiple times until completion."""
    mock_token_store = MagicMock()
    mock_token_store.is_authenticated = True
    mock_token_store.load_token.return_value = "fake-token"

    mock_client = MagicMock()
    mock_client.submit_evaluation.return_value = "eval-poll-test"

    # First call: pending, second call: completed
    mock_client.get_status.side_effect = [
        EvaluationStatus(
            evaluation_id="eval-poll-test",
            status="pending",
            role_category="engineering",
        ),
        EvaluationStatus(
            evaluation_id="eval-poll-test",
            status="completed",
            role_category="engineering",
            result={
                "overall_score": 75,
                "model_scores": {},
                "layer_scores": {},
            },
            completed_at="2026-03-20T12:00:00Z",
        ),
    ]

    runner = CliRunner()
    with runner.isolated_filesystem():
        with patch("aiq.cli.TokenStore", return_value=mock_token_store), \
             patch("aiq.cli.AIQClient", return_value=mock_client), \
             patch("aiq.cli.time.sleep"):  # skip actual sleep
            result = runner.invoke(
                main,
                ["evaluate", "--auto-approve", "--role", "engineering", "-o", "test-report.pdf"],
            )

    assert result.exit_code == 0, f"CLI failed: {result.output}"
    # Should have polled twice
    assert mock_client.get_status.call_count == 2
    assert "complete" in result.output.lower()


def test_cli_evaluate_api_failure() -> None:
    """Evaluate handles API submission failure gracefully."""
    mock_token_store = MagicMock()
    mock_token_store.is_authenticated = True
    mock_token_store.load_token.return_value = "fake-token"

    mock_client = MagicMock()
    mock_client.submit_evaluation.side_effect = Exception("Connection refused")

    runner = CliRunner()
    with patch("aiq.cli.TokenStore", return_value=mock_token_store), \
         patch("aiq.cli.AIQClient", return_value=mock_client):
        result = runner.invoke(
            main,
            ["evaluate", "--auto-approve", "--role", "engineering"],
        )

    assert result.exit_code == 1
    assert "submission failed" in result.output.lower() or "connection refused" in result.output.lower()


def test_cli_evaluate_eval_failed() -> None:
    """Evaluate handles evaluation failure status."""
    mock_token_store = MagicMock()
    mock_token_store.is_authenticated = True
    mock_token_store.load_token.return_value = "fake-token"

    mock_client = MagicMock()
    mock_client.submit_evaluation.return_value = "eval-fail-test"
    mock_client.get_status.return_value = EvaluationStatus(
        evaluation_id="eval-fail-test",
        status="failed",
        role_category="engineering",
        error="Internal model error",
    )

    runner = CliRunner()
    with patch("aiq.cli.TokenStore", return_value=mock_token_store), \
         patch("aiq.cli.AIQClient", return_value=mock_client):
        result = runner.invoke(
            main,
            ["evaluate", "--auto-approve", "--role", "engineering"],
        )

    assert result.exit_code == 1
    assert "failed" in result.output.lower()


def test_cli_init() -> None:
    runner = CliRunner()
    # Provide inputs: empty company, role=1 (Software Engineer), empty email
    result = runner.invoke(main, ["init"], input="\n1\n\n")
    assert result.exit_code == 0
    # Should show the setup panel or profile saved message
    assert "Profile saved" in result.output or "AIQ" in result.output


def test_cli_login() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["login"])
    assert result.exit_code == 0
    # Stub message about API not being live
    assert "stub" in result.output.lower() or "login" in result.output.lower()


def test_cli_logout_not_logged_in() -> None:
    """Logout when not authenticated should not crash."""
    runner = CliRunner()
    result = runner.invoke(main, ["logout"])
    assert result.exit_code == 0


def test_cli_delete_account_not_logged_in() -> None:
    """Delete-account when not logged in should report error gracefully."""
    runner = CliRunner()
    result = runner.invoke(main, ["delete-account"])
    assert result.exit_code == 0
    assert "logged in" in result.output.lower() or "authenticate" in result.output.lower()
