import os
from typing import Any, Optional

import httpx


class P21ODataClient:
    def __init__(self, base_url: Optional[str] = None, api_key: Optional[str] = None):
        self.base_url = (base_url or os.getenv("P21_ODATA_BASE_URL", "")).rstrip("/")
        self.api_key = api_key or os.getenv("P21_ODATA_API_KEY")

    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {"Accept": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def test_connection(self) -> dict[str, Any]:
        if not self.base_url:
            raise ValueError("P21_ODATA_BASE_URL is required")
        url = f"{self.base_url}/$metadata"
        with httpx.Client(timeout=15.0) as client:
            response = client.get(url, headers=self._headers())
        response.raise_for_status()
        return {
            "status": "ok",
            "endpoint": url,
            "http_status": response.status_code,
        }
