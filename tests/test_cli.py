"""Tests for AIQ CLI."""

from click.testing import CliRunner

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


def test_cli_evaluate() -> None:
    runner = CliRunner()
    # auto-approve so it doesn't wait for stdin
    result = runner.invoke(main, ["evaluate", "--auto-approve"])
    assert result.exit_code == 0
    assert "valuat" in result.output.lower()


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
