"""Device code OAuth flow -- like `gh auth login`.

Flow:
1. CLI requests a device code from the API
2. API returns a user_code and verification_uri
3. CLI displays the code and opens the browser
4. User enters the code in the browser
5. CLI polls the API until the user completes auth
6. API returns an access token
7. CLI stores the token locally
"""

from __future__ import annotations

import contextlib
import time
import webbrowser

import httpx
from rich.console import Console

from aiq.auth.token_store import TokenStore

console = Console()


class DeviceCodeAuth:
    """Handles the device code OAuth flow for CLI authentication."""

    def __init__(
        self,
        api_base_url: str = "https://api.aiq.dev",
        token_store: TokenStore | None = None,
    ) -> None:
        self._api_base_url = api_base_url.rstrip("/")
        self._token_store = token_store or TokenStore()

    def login(self) -> bool:
        """Run the full device code login flow. Returns True on success."""
        # Check if already authenticated
        if self._token_store.is_authenticated:
            console.print("[green]Already authenticated.[/green]")
            return True

        # Step 1: Request device code
        try:
            response = httpx.post(
                f"{self._api_base_url}/auth/device/code",
                json={"client_id": "aiq-cli"},
                timeout=30,
            )
            response.raise_for_status()
        except httpx.HTTPError as e:
            console.print(f"[red]Failed to initiate login: {e}[/red]")
            return False

        data = response.json()
        device_code: str = data["device_code"]
        user_code: str = data["user_code"]
        verification_uri: str = data["verification_uri"]
        interval: int = data.get("interval", 5)
        expires_in: int = data.get("expires_in", 900)

        # Step 2: Display code and open browser
        console.print()
        console.print(f"[bold]Open this URL in your browser:[/bold] {verification_uri}")
        console.print(f"[bold]Enter this code:[/bold] [cyan]{user_code}[/cyan]")
        console.print()

        with contextlib.suppress(Exception):
            webbrowser.open(verification_uri)

        # Step 3: Poll for token
        console.print("Waiting for authorization...", end="")
        deadline = time.time() + expires_in

        while time.time() < deadline:
            time.sleep(interval)
            try:
                poll_response = httpx.post(
                    f"{self._api_base_url}/auth/device/token",
                    json={
                        "client_id": "aiq-cli",
                        "device_code": device_code,
                        "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                    },
                    timeout=30,
                )
            except httpx.HTTPError:
                console.print(".", end="")
                continue

            if poll_response.status_code == 200:
                token_data = poll_response.json()
                self._token_store.save_token(
                    access_token=token_data["access_token"],
                    expires_at=int(time.time()) + token_data.get("expires_in", 86400),
                )
                console.print()
                console.print("[green]Login successful![/green]")
                return True

            # 428 = authorization_pending, keep polling
            if poll_response.status_code == 428:
                console.print(".", end="")
                continue

            # Other error
            console.print()
            console.print(f"[red]Auth error: {poll_response.status_code}[/red]")
            return False

        console.print()
        console.print("[red]Login timed out. Please try again.[/red]")
        return False

    def logout(self) -> None:
        """Clear stored credentials."""
        self._token_store.clear()
        console.print("[green]Logged out successfully.[/green]")

    def get_token(self) -> str | None:
        """Get a valid access token, or None if not authenticated."""
        return self._token_store.load_token()
