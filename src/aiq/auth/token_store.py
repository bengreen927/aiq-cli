"""Local token persistence -- stores auth tokens securely on disk."""

from __future__ import annotations

import json
import os
import stat
import time
from pathlib import Path


class TokenStore:
    """Stores and retrieves auth tokens from a local JSON file.

    Token file is created with 0o600 permissions (owner read/write only).
    """

    def __init__(self, config_dir: Path | None = None) -> None:
        self._config_dir = config_dir or (Path.home() / ".aiq")
        self._token_file = self._config_dir / "auth.json"

    def save_token(self, access_token: str, expires_at: int) -> None:
        """Save an access token with expiration timestamp."""
        self._config_dir.mkdir(parents=True, exist_ok=True)

        data = {
            "access_token": access_token,
            "expires_at": expires_at,
        }

        self._token_file.write_text(json.dumps(data), encoding="utf-8")
        # Set file permissions to owner-only
        os.chmod(self._token_file, stat.S_IRUSR | stat.S_IWUSR)

    def load_token(self) -> str | None:
        """Load a valid (non-expired) access token, or None."""
        if not self._token_file.is_file():
            return None

        try:
            data = json.loads(self._token_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

        expires_at = data.get("expires_at", 0)
        if time.time() >= expires_at:
            return None

        return data.get("access_token")  # type: ignore[no-any-return]

    def clear(self) -> None:
        """Remove stored token."""
        if self._token_file.is_file():
            self._token_file.unlink()

    @property
    def is_authenticated(self) -> bool:
        """Check if a valid token is available."""
        return self.load_token() is not None
