"""AIQ CLI entry point."""

from typing import Optional

import click


@click.group()
@click.version_option()
def main() -> None:
    """AIQ - Evaluate your personalized AI setup."""


@main.command()
def scan() -> None:
    """Scan your local AI setup."""
    click.echo("Scanning AI setup...")


@main.command()
def evaluate() -> None:
    """Run a full AIQ evaluation."""
    click.echo("Starting evaluation...")


@main.command()
@click.argument("company", required=False)
def init(company: Optional[str] = None) -> None:
    """Initialize AIQ with your profile."""
    click.echo("Initializing AIQ profile...")
