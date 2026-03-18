"""Tests for PII auto-scrub."""

from aiq.scrubber.pii import PiiScrubber


def test_scrubber_replaces_email() -> None:
    scrubber = PiiScrubber()
    text = "Contact john@example.com for details."
    result = scrubber.scrub(text)
    assert "john@example.com" not in result.scrubbed_text
    assert "[EMAIL]" in result.scrubbed_text
    assert result.replacement_count > 0


def test_scrubber_replaces_file_paths_with_username() -> None:
    scrubber = PiiScrubber()
    text = "Config at /Users/johndoe/project/.claude/CLAUDE.md"
    result = scrubber.scrub(text)
    assert "johndoe" not in result.scrubbed_text
    assert "[USER]" in result.scrubbed_text


def test_scrubber_replaces_api_keys() -> None:
    scrubber = PiiScrubber()
    text = "API_KEY=sk-abc123def456ghi789jkl012mno345pqr678stu901vwx"
    result = scrubber.scrub(text)
    assert "sk-abc123" not in result.scrubbed_text
    assert "[API_KEY]" in result.scrubbed_text


def test_scrubber_replaces_ip_addresses() -> None:
    scrubber = PiiScrubber()
    text = "Server at 192.168.1.100 and 10.0.0.1"
    result = scrubber.scrub(text)
    assert "192.168.1.100" not in result.scrubbed_text
    assert "[IP_ADDRESS]" in result.scrubbed_text


def test_scrubber_replaces_phone_numbers() -> None:
    scrubber = PiiScrubber()
    text = "Call 555-123-4567 or (555) 987-6543"
    result = scrubber.scrub(text)
    assert "555-123-4567" not in result.scrubbed_text
    assert "[PHONE]" in result.scrubbed_text


def test_scrubber_replaces_declared_company() -> None:
    scrubber = PiiScrubber(company_name="Acme Corp")
    text = "We work at Acme Corp building medical devices."
    result = scrubber.scrub(text)
    assert "Acme Corp" not in result.scrubbed_text
    assert "[COMPANY]" in result.scrubbed_text


def test_scrubber_replaces_ssh_keys() -> None:
    scrubber = PiiScrubber()
    text = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQ user@host"
    result = scrubber.scrub(text)
    assert "AAAAB3" not in result.scrubbed_text
    assert "[SSH_KEY]" in result.scrubbed_text


def test_scrubber_preserves_non_pii() -> None:
    scrubber = PiiScrubber()
    text = "Use python3 for all scripts. Follow ISO 14971."
    result = scrubber.scrub(text)
    assert result.scrubbed_text == text
    assert result.replacement_count == 0


def test_scrubber_reports_categories() -> None:
    scrubber = PiiScrubber()
    text = "Email: user@test.com, IP: 10.0.0.1"
    result = scrubber.scrub(text)
    assert "email" in result.categories_found
    assert "ip_address" in result.categories_found


def test_scrubber_dual_layer_replacement_not_deletion() -> None:
    """PII should be replaced with placeholders, never deleted."""
    scrubber = PiiScrubber()
    text = "Send report to admin@company.com at 192.168.1.1"
    result = scrubber.scrub(text)
    # The sentence structure should be preserved
    assert "Send report to" in result.scrubbed_text
    assert "at" in result.scrubbed_text
    # Placeholders present
    assert "[EMAIL]" in result.scrubbed_text
    assert "[IP_ADDRESS]" in result.scrubbed_text
