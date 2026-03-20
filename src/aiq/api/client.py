"""HTTP client for the AIQ evaluation API."""
from dataclasses import dataclass
from typing import Any, Dict, Optional

import httpx

from aiq.extractor.models import MacfDocument, MacfEntry

DEFAULT_BASE_URL = "https://api.aiq.dev"
DEFAULT_TIMEOUT = 30.0


@dataclass
class EvaluationStatus:
    evaluation_id: str
    status: str
    role_category: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    completed_at: Optional[str] = None


class AIQClient:
    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        token: Optional[str] = None,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout = timeout

    def _headers(self) -> Dict[str, str]:
        headers: Dict[str, str] = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    @staticmethod
    def _macf_to_api_format(doc: MacfDocument) -> Dict[str, Any]:
        """Convert CLI MacfDocument to API format (entry_type -> type)."""

        def entry_to_dict(entry: MacfEntry) -> Dict[str, str]:
            return {
                "source": entry.source,
                "type": entry.entry_type,
                "content": entry.content,
                "category": entry.category,
            }

        return {
            "domain_knowledge": [entry_to_dict(e) for e in doc.domain_knowledge],
            "workflow_patterns": [entry_to_dict(e) for e in doc.workflow_patterns],
            "tool_integrations": [entry_to_dict(e) for e in doc.tool_integrations],
        }

    def submit_evaluation(
        self,
        config: MacfDocument,
        role_category: str,
        temporal_fingerprint: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Submit MACF config for evaluation. Returns evaluation_id."""
        payload = {
            "config": self._macf_to_api_format(config),
            "role_category": role_category,
            "temporal_fingerprint": temporal_fingerprint or {},
        }
        response = httpx.post(
            f"{self.base_url}/evaluate",
            json=payload,
            headers=self._headers(),
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()["evaluation_id"]  # type: ignore[no-any-return]

    def get_status(self, evaluation_id: str) -> EvaluationStatus:
        """Poll evaluation status."""
        response = httpx.get(
            f"{self.base_url}/evaluations/{evaluation_id}",
            headers=self._headers(),
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()
        return EvaluationStatus(
            evaluation_id=data["evaluation_id"],
            status=data["status"],
            role_category=data.get("role_category", ""),
            result=data.get("result"),
            error=data.get("error"),
            completed_at=data.get("completed_at"),
        )
