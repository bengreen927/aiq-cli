"""Regex patterns for PII detection.

Each pattern is a tuple of (category, compiled_regex, replacement_placeholder).
Order matters — patterns are applied sequentially, so more specific patterns
should come before more general ones.
"""

from __future__ import annotations

import re

# Type alias for a pattern entry
PatternEntry = tuple[str, "re.Pattern[str]", str]


def get_patterns() -> list[PatternEntry]:
    """Return ordered list of PII detection patterns."""
    return [
        # SSH keys
        (
            "ssh_key",
            re.compile(r"ssh-(?:rsa|ed25519|dsa|ecdsa)\s+[A-Za-z0-9+/=]+(?:\s+\S+)?"),
            "[SSH_KEY]",
        ),
        # API keys / tokens (common formats)
        (
            "api_key",
            re.compile(
                r"((?:api[_-]?key|token|secret|password|credential|auth)"
                r"[\s]*[=:]\s*['\"]?)[A-Za-z0-9_\-]{20,}['\"]?",
                re.IGNORECASE,
            ),
            r"\1[API_KEY]",
        ),
        # API keys by prefix (sk-, pk-, ghp_, etc.)
        (
            "api_key",
            re.compile(
                r"\b(?:sk|pk|ghp|gho|ghu|ghs|ghr|xoxb|xoxp|xapp)"
                r"[-_][A-Za-z0-9_\-]{16,}\b"
            ),
            "[API_KEY]",
        ),
        # Email addresses
        (
            "email",
            re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
            "[EMAIL]",
        ),
        # Phone numbers (US formats)
        (
            "phone",
            re.compile(r"(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),
            "[PHONE]",
        ),
        # IP addresses (IPv4)
        (
            "ip_address",
            re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
            "[IP_ADDRESS]",
        ),
        # File paths containing usernames (macOS and Linux)
        (
            "file_path",
            re.compile(r"/(?:Users|home)/([A-Za-z0-9._-]+)"),
            "/Users/[USER]",
        ),
        # Windows-style paths with usernames
        (
            "file_path",
            re.compile(r"C:\\Users\\([A-Za-z0-9._-]+)"),
            "C:\\Users\\[USER]",
        ),
    ]
