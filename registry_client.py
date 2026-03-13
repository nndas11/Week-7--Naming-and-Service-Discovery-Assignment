import random
import time
from typing import Any, Dict, List, Optional

import requests


class RegistryClient:
    def __init__(
        self,
        registry_url: str = "http://localhost:5001",
        timeout: float = 3.0,
        max_retries: int = 5,
        backoff_base: float = 0.5,
    ) -> None:
        self.registry_url = registry_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_base = backoff_base

    def _sleep_backoff(self, attempt: int) -> None:
        jitter = random.uniform(0.0, 0.25)
        time.sleep(self.backoff_base * (2 ** attempt) + jitter)

    def _request(self, method: str, path: str, **kwargs: Any) -> Optional[requests.Response]:
        url = f"{self.registry_url}{path}"
        for attempt in range(self.max_retries):
            try:
                return requests.request(method, url, timeout=self.timeout, **kwargs)
            except requests.exceptions.RequestException:
                self._sleep_backoff(attempt)
        return None

    def register(self, service: str, address: str) -> bool:
        response = self._request(
            "POST",
            "/register",
            json={"service": service, "address": address},
            headers={"Content-Type": "application/json"},
        )
        return bool(response and response.status_code in (200, 201))

    def heartbeat(self, service: str, address: str) -> bool:
        response = self._request(
            "POST",
            "/heartbeat",
            json={"service": service, "address": address},
            headers={"Content-Type": "application/json"},
        )
        return bool(response and response.status_code == 200)

    def deregister(self, service: str, address: str) -> bool:
        response = self._request(
            "POST",
            "/deregister",
            json={"service": service, "address": address},
            headers={"Content-Type": "application/json"},
        )
        return bool(response and response.status_code == 200)

    def discover(self, service: str) -> List[Dict[str, Any]]:
        response = self._request("GET", f"/discover/{service}")
        if not response or response.status_code != 200:
            return []
        try:
            data = response.json()
        except ValueError:
            return []
        return data.get("instances", [])
