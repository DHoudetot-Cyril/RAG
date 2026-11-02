"""Client HTTP de l'API RAG École, partagé par les trois interfaces Streamlit."""

from __future__ import annotations

import json
from collections.abc import Iterator

import requests


class ApiError(RuntimeError):
    pass


class ApiClient:
    def __init__(self, base_url: str, api_key: str, timeout: float = 180.0):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers["X-API-Key"] = api_key
        self.timeout = timeout

    def _request(self, method: str, path: str, **kwargs) -> requests.Response:
        kwargs.setdefault("timeout", self.timeout)
        try:
            response = self.session.request(method, self.base_url + path, **kwargs)
        except requests.RequestException as exc:
            raise ApiError(f"Impossible de joindre l'API ({exc.__class__.__name__}).") from exc
        if response.status_code >= 400:
            try:
                detail = response.json().get("detail", response.text)
            except ValueError:
                detail = response.text
            raise ApiError(f"{response.status_code} : {detail}")
        return response

    def health(self) -> dict:
        return self._request("GET", "/health", timeout=5).json()

    def me(self) -> dict:
        return self._request("GET", "/me").json()

    def documents(self, level: str | None = None) -> list[dict]:
        params = {"level": level} if level else None
        return self._request("GET", "/documents", params=params).json()

    def upload(self, filename: str, data: bytes, level: str) -> dict:
        return self._request("POST", "/documents", data={"level": level}, files={"file": (filename, data)}).json()

    def delete(self, level: str, document_id: str) -> dict:
        return self._request("DELETE", f"/documents/{level}/{document_id}").json()

    def stream_chat(self, question: str, history: list[dict], levels: list[str] | None = None) -> Iterator[dict]:
        payload = {"question": question, "history": history, "levels": levels}
        response = self._request("POST", "/chat/stream", json=payload, stream=True)
        with response:
            for line in response.iter_lines(decode_unicode=True):
                if line:
                    yield json.loads(line)
