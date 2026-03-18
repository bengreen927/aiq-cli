"""Tests for device code auth flow and token storage."""

import os
import stat
import time
from pathlib import Path

from aiq.auth.device_flow import DeviceCodeAuth
from aiq.auth.token_store import TokenStore


def test_token_store_save_and_load(tmp_path: Path) -> None:
    store = TokenStore(config_dir=tmp_path)
    store.save_token("test-access-token", expires_at=int(time.time()) + 3600)
    loaded = store.load_token()
    assert loaded == "test-access-token"


def test_token_store_expired(tmp_path: Path) -> None:
    store = TokenStore(config_dir=tmp_path)
    store.save_token("expired-token", expires_at=int(time.time()) - 100)
    loaded = store.load_token()
    assert loaded is None


def test_token_store_clear(tmp_path: Path) -> None:
    store = TokenStore(config_dir=tmp_path)
    store.save_token("token-to-clear", expires_at=int(time.time()) + 3600)
    store.clear()
    loaded = store.load_token()
    assert loaded is None


def test_token_store_no_token(tmp_path: Path) -> None:
    store = TokenStore(config_dir=tmp_path)
    loaded = store.load_token()
    assert loaded is None


def test_token_store_file_permissions(tmp_path: Path) -> None:
    store = TokenStore(config_dir=tmp_path)
    store.save_token("secure-token", expires_at=int(time.time()) + 3600)
    token_file = tmp_path / "auth.json"
    # File should exist
    assert token_file.exists()
    # On Unix, should be readable only by owner (0o600)
    mode = os.stat(token_file).st_mode
    assert not (mode & stat.S_IRGRP)  # No group read
    assert not (mode & stat.S_IROTH)  # No other read


def test_device_code_auth_api_url() -> None:
    auth = DeviceCodeAuth(api_base_url="https://api.aiq.dev")
    assert auth._api_base_url == "https://api.aiq.dev"
