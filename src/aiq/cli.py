"""AIQ CLI entry point."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from aiq.auth.token_store import TokenStore
from aiq.extractor.macf import MacfExtractor
from aiq.models import UserProfile
from aiq.review.interactive import ReviewSession
from aiq.scanner.registry import ScannerRegistry
from aiq.scrubber.pii import PiiScrubber

console = Console()

_PROFILE_PATH = Path.home() / ".aiq" / "profile.json"

_ROLE_CATEGORIES = [
    "Software Engineer",
    "Product Manager",
    "Data Scientist / ML Engineer",
    "Regulatory / QA / Compliance",
    "Designer / UX",
    "DevOps / Platform Engineer",
    "Research Scientist",
    "Business / Operations",
    "Other",
]


def _load_profile() -> Optional[UserProfile]:  # noqa: UP045
    """Load user profile from disk, or None if not initialized."""
    if not _PROFILE_PATH.is_file():
        return None
    try:
        data = json.loads(_PROFILE_PATH.read_text(encoding="utf-8"))
        return UserProfile(**data)
    except Exception:
        return None


def _save_profile(profile: UserProfile) -> None:
    """Persist user profile to disk."""
    _PROFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _PROFILE_PATH.write_text(profile.model_dump_json(indent=2), encoding="utf-8")


@click.group()
@click.version_option(version="0.1.0", prog_name="aiq")
def main() -> None:
    """AIQ - Evaluate your personalized AI setup."""


# ---------------------------------------------------------------------------
# aiq init
# ---------------------------------------------------------------------------


@main.command()
def init() -> None:
    """Initialize AIQ with your profile."""
    console.print()
    console.print(Panel.fit("[bold cyan]AIQ Setup[/bold cyan]", subtitle="Let's get started"))
    console.print()

    existing = _load_profile()
    if existing:
        console.print("[yellow]Profile already exists. Reinitializing will overwrite it.[/yellow]")
        if not click.confirm("Continue?", default=False):
            console.print("Cancelled.")
            return
        console.print()

    # Company name
    company_name = click.prompt(
        "Company / organization name (optional, press Enter to skip)", default=""
    )

    # Role category
    console.print()
    console.print("[bold]Select your role category:[/bold]")
    for i, role in enumerate(_ROLE_CATEGORIES, 1):
        console.print(f"  {i}. {role}")
    console.print()

    role_index = click.prompt(
        "Enter number (1-9)",
        type=click.IntRange(1, len(_ROLE_CATEGORIES)),
        default=9,
    )
    role_category = _ROLE_CATEGORIES[role_index - 1]

    # Email (optional)
    email = click.prompt("Email address (optional, press Enter to skip)", default="")

    profile = UserProfile(
        company_name=company_name if company_name else None,
        role_category=role_category,
        email=email if email else None,
    )
    _save_profile(profile)

    console.print()
    console.print(
        Panel.fit(
            f"[green]Profile saved![/green]\n"
            f"Role: [bold]{role_category}[/bold]"
            + (f"\nCompany: [bold]{company_name}[/bold]" if company_name else ""),
            title="AIQ Init Complete",
        )
    )
    console.print()
    console.print("Run [bold cyan]aiq scan[/bold cyan] to discover your AI setup.")
    console.print("Run [bold cyan]aiq evaluate[/bold cyan] to run a full evaluation.")


# ---------------------------------------------------------------------------
# aiq scan
# ---------------------------------------------------------------------------


@main.command()
def scan() -> None:
    """Scan your local AI setup."""
    console.print()
    console.print(
        Panel.fit("[bold cyan]AIQ Scan[/bold cyan]", subtitle="Discovering your AI setup")
    )
    console.print()

    registry = ScannerRegistry.default()

    all_results = []
    for scanner_name, scanner in registry.iter_scanners():
        console.print(f"  Scanning [bold]{scanner_name}[/bold]...", end="")
        result = scanner.scan()
        all_results.append(result)
        if result.errors:
            n_err = len(result.errors)
            console.print(f" [yellow]{result.item_count} items[/yellow] ({n_err} errors)")
        else:
            console.print(f" [green]{result.item_count} items[/green]")

    console.print()

    # Summary table
    table = Table(title="Scan Results", show_header=True, header_style="bold cyan")
    table.add_column("Scanner", style="bold", min_width=16)
    table.add_column("Items", justify="right", min_width=6)
    table.add_column("Errors", justify="right", min_width=6)
    table.add_column("Categories", min_width=30)

    total_items = 0
    for result in all_results:
        cats = sorted({item.category.value for item in result.items})
        cats_str = ", ".join(cats[:4])
        if len(cats) > 4:
            cats_str += f" +{len(cats) - 4}"
        error_str = f"[red]{len(result.errors)}[/red]" if result.errors else "0"
        table.add_row(result.scanner_name, str(result.item_count), error_str, cats_str)
        total_items += result.item_count

    console.print(table)
    console.print()
    console.print(f"[bold]Total items discovered:[/bold] [green]{total_items}[/green]")
    console.print()
    console.print(
        "Run [bold cyan]aiq evaluate[/bold cyan] to analyze your setup and generate a report."
    )


# ---------------------------------------------------------------------------
# aiq evaluate
# ---------------------------------------------------------------------------


@main.command()
@click.option("--output", "-o", default="aiq-report.pdf", help="Output path for the PDF report.")
@click.option(
    "--auto-approve", is_flag=True, default=False, help="Skip interactive review, approve all."
)
def evaluate(output: str, auto_approve: bool) -> None:
    """Run a full AIQ evaluation."""
    console.print()
    console.print(
        Panel.fit(
            "[bold cyan]AIQ Evaluation[/bold cyan]",
            subtitle="Scan → Extract → Scrub → Review → Report",
        )
    )
    console.print()

    profile = _load_profile()
    company_name = profile.company_name if profile else None

    # --- Step 1: Scan ---
    console.print("[bold]Step 1/4:[/bold] Scanning AI setup...")
    registry = ScannerRegistry.default()
    all_results = registry.scan_all()
    all_items = [item for result in all_results for item in result.items]
    n_items = len(all_items)
    n_scanners = len(all_results)
    console.print(f"  Found [green]{n_items}[/green] items across {n_scanners} scanners.")
    console.print()

    # --- Step 2: Extract MACF ---
    console.print("[bold]Step 2/4:[/bold] Extracting configuration (MACF)...")
    extractor = MacfExtractor()
    macf_doc = extractor.extract(all_items, evaluations=[])
    total_entries = (
        len(macf_doc.domain_knowledge)
        + len(macf_doc.workflow_patterns)
        + len(macf_doc.tool_integrations)
    )
    console.print(f"  Extracted [green]{total_entries}[/green] entries into MACF format.")
    console.print(f"    Domain knowledge: {len(macf_doc.domain_knowledge)}")
    console.print(f"    Workflow patterns: {len(macf_doc.workflow_patterns)}")
    console.print(f"    Tool integrations: {len(macf_doc.tool_integrations)}")
    console.print()

    # --- Step 3: Scrub PII ---
    console.print("[bold]Step 3/4:[/bold] Scrubbing PII...")
    scrubber = PiiScrubber(company_name=company_name)
    macf_json = macf_doc.model_dump_json(indent=2)
    scrub_result = scrubber.scrub_macf(macf_json)
    if scrub_result.replacement_count > 0:
        console.print(
            f"  Replaced [yellow]{scrub_result.replacement_count}[/yellow] PII instances "
            f"({', '.join(scrub_result.categories_found)})."
        )
    else:
        console.print("  No PII detected.")
    console.print()

    # --- Step 4: Interactive Review ---
    console.print("[bold]Step 4/4:[/bold] Pre-transmission review...")
    session = ReviewSession(macf_doc)

    if auto_approve or not sys.stdin.isatty():
        # Non-interactive mode: approve all
        session.approve_all()
        console.print(f"  Auto-approved all {session.total_entries} entries.")
    else:
        # Interactive review
        console.print(f"  {session.total_entries} entries to review.")
        console.print(
            "  Press [bold]a[/bold]=approve, [bold]r[/bold]=redact, "
            "[bold]A[/bold]=approve all, [bold]q[/bold]=quit review"
        )
        console.print()

        for idx, section, entry in session.get_all_entries():
            console.print(
                f"[{idx + 1}/{session.total_entries}] "
                f"[cyan]{section}[/cyan] | [bold]{entry.source}[/bold]"
            )
            # Show truncated content preview
            preview = entry.content[:200].replace("\n", " ")
            if len(entry.content) > 200:
                preview += "..."
            console.print(f"  {preview}", style="dim")

            choice = click.prompt("  Action", default="a", show_default=True)
            if choice.lower() == "r":
                session.redact(idx)
            elif choice.upper() == "A":
                # Approve remaining
                for remaining_idx, _, __ in session.get_all_entries():
                    if remaining_idx >= idx:
                        session.approve(remaining_idx)
                console.print(f"  Approved remaining {session.total_entries - idx} entries.")
                break
            elif choice.lower() == "q":
                console.print("  Exiting review. Unreviewed entries will be excluded.")
                break
            else:
                session.approve(idx)

    approved_doc = session.get_approved_document()
    approved_count = (
        len(approved_doc.domain_knowledge)
        + len(approved_doc.workflow_patterns)
        + len(approved_doc.tool_integrations)
    )
    redacted = session.redacted_count
    console.print()

    if redacted > 0:
        console.print(f"  [yellow]{redacted}[/yellow] entries redacted.")
    console.print(f"  [green]{approved_count}[/green] entries approved for transmission.")
    console.print()

    # --- API Stub ---
    console.print("[bold]Sending to API...[/bold] (stub — API not yet live)")
    console.print("  Would POST scrubbed MACF to https://api.aiq.dev/v1/evaluate")
    console.print("  Would receive evaluation_id, overall_score, model_scores, layer_scores")
    console.print()

    # --- Generate local PDF report ---
    output_path = Path(output)
    try:
        from aiq.report.pdf import PdfReportGenerator, ReportData

        report_data = ReportData(
            user_email=profile.email if profile and profile.email else "Not provided",
            role_category=profile.role_category if profile and profile.role_category else "Unknown",
            overall_score=0,
            model_scores={"claude": 0, "gpt": 0, "gemini": 0},
            layer_scores={
                "execution": 0,
                "robustness": 0,
                "constraint_satisfaction": 0,
                "ground_truth": 0,
                "telemetry": 0,
                "ai_judge": 0,
            },
            challenge_version="v1.0",
            evaluation_id="stub-evaluation",
        )
        generator = PdfReportGenerator()
        generator.generate(report_data, output_path)
        console.print(f"[green]Local PDF report saved:[/green] [bold]{output_path}[/bold]")
    except Exception as e:
        console.print(f"[yellow]PDF generation skipped:[/yellow] {e}")

    console.print()
    console.print(
        Panel.fit(
            "[bold green]Evaluation complete![/bold green]\n"
            "[dim]Real scores will be available once the AIQ API is live.[/dim]",
            title="AIQ Evaluation",
        )
    )


# ---------------------------------------------------------------------------
# aiq login
# ---------------------------------------------------------------------------


@main.command()
def login() -> None:
    """Authenticate with AIQ (device code flow)."""
    console.print()
    console.print(
        Panel.fit(
            "[bold cyan]AIQ Login[/bold cyan]",
            subtitle="Device code authentication",
        )
    )
    console.print()
    console.print("[yellow]Note: API login is not yet live. This is a stub.[/yellow]")
    console.print()
    console.print("Would initiate device code flow at https://api.aiq.dev/auth/device/code")
    console.print("When the API is live, run this command to authenticate.")
    console.print()
    console.print("For now, [bold cyan]aiq evaluate[/bold cyan] works fully offline.")


# ---------------------------------------------------------------------------
# aiq logout
# ---------------------------------------------------------------------------


@main.command()
def logout() -> None:
    """Clear stored authentication token."""
    store = TokenStore()
    if not store.is_authenticated:
        console.print("Not currently logged in.")
        return
    store.clear()
    console.print("[green]Logged out successfully.[/green]")


# ---------------------------------------------------------------------------
# aiq delete-account
# ---------------------------------------------------------------------------


@main.command("delete-account")
def delete_account() -> None:
    """Delete your AIQ account and all associated data."""
    console.print()
    console.print("[bold red]Delete Account[/bold red]")
    console.print()
    console.print(
        "[yellow]Warning: This will permanently delete your AIQ account "
        "and all associated scores.[/yellow]"
    )
    console.print()

    store = TokenStore()
    if not store.is_authenticated:
        console.print("[red]Not logged in. Authenticate first with `aiq login`.[/red]")
        return

    if not click.confirm("Are you absolutely sure?", default=False):
        console.print("Cancelled.")
        return

    console.print()
    console.print("[yellow]Note: API delete-account is not yet live. This is a stub.[/yellow]")
    console.print("Would DELETE https://api.aiq.dev/v1/account")
    console.print()
    store.clear()
    console.print("[green]Local credentials cleared.[/green]")
