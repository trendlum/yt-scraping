from __future__ import annotations

from typing import Any

import requests

from ..constants import DEFAULT_TIMEOUT
from ..exceptions import SupabaseAPIError
from .http import build_retry_session


class SupabaseClient:
    def __init__(
        self,
        supabase_url: str,
        supabase_key: str,
        *,
        timeout: int = DEFAULT_TIMEOUT,
        session: requests.Session | None = None,
    ) -> None:
        self.supabase_url = supabase_url.rstrip("/")
        self.supabase_key = supabase_key
        self.timeout = timeout
        self.session = session or build_retry_session()

    def _headers(self) -> dict[str, str]:
        return {
            "apikey": self.supabase_key,
            "Authorization": f"Bearer {self.supabase_key}",
            "Content-Type": "application/json",
        }

    def request(
        self,
        method: str,
        path: str,
        *,
        params: Any | None = None,
        json_body: Any | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> Any:
        url = f"{self.supabase_url}/rest/v1/{path.lstrip('/')}"
        headers = self._headers()
        if extra_headers:
            headers.update(extra_headers)

        try:
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                json=json_body,
                headers=headers,
                timeout=self.timeout,
            )
            response.raise_for_status()
        except requests.Timeout as exc:
            raise SupabaseAPIError(f"Timeout while calling Supabase path {path}") from exc
        except requests.HTTPError as exc:
            if exc.response is not None:
                body = exc.response.text.strip()
                if not body:
                    body = exc.response.reason or "<empty body>"
                detail = f"status={exc.response.status_code}, body={body}"
            else:
                detail = str(exc)
            raise SupabaseAPIError(f"HTTP error while calling Supabase path {path}: {detail}") from exc
        except requests.RequestException as exc:
            raise SupabaseAPIError(f"Request failed while calling Supabase path {path}: {exc}") from exc

        if not response.text.strip():
            return None

        try:
            return response.json()
        except ValueError as exc:
            raise SupabaseAPIError(f"Invalid JSON received from Supabase path {path}") from exc
