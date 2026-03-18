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
    assert "Scanning" in result.output


def test_cli_evaluate() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["evaluate"])
    assert result.exit_code == 0
    assert "evaluation" in result.output.lower()


def test_cli_init() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["init"])
    assert result.exit_code == 0
    assert "Initializing" in result.output
