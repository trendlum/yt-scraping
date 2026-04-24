from __future__ import annotations

import requests

from yt_insights.clients.supabase import SupabaseClient
from yt_insights.exceptions import SupabaseAPIError
from yt_insights.repositories.supabase import SupabaseRepository


class _EmptyBodySession:
    def request(self, method, url, params=None, json=None, headers=None, timeout=None):
        response = requests.Response()
        response.status_code = 400
        response.reason = "Bad Request"
        response.url = url
        response._content = b""
        response.request = requests.Request(method=method, url=url).prepare()
        return response


class _FailingClient:
    def request(self, *args, **kwargs):
        raise SupabaseAPIError("HTTP error while calling Supabase path yt_videos: status=400, body=Bad Request")


def test_supabase_client_request_includes_status_and_reason_on_empty_error_body() -> None:
    client = SupabaseClient(
        "https://example.supabase.co",
        "secret",
        session=_EmptyBodySession(),
    )

    try:
        client.request("GET", "yt_videos")
    except SupabaseAPIError as exc:
        message = str(exc)
    else:
        raise AssertionError("SupabaseAPIError was not raised")

    assert "status=400" in message
    assert "body=Bad Request" in message


def test_supabase_repository_wraps_upsert_errors_with_table_and_ids() -> None:
    repository = SupabaseRepository(_FailingClient())

    try:
        repository.upsert_current_videos(
            [
                {"video_id": "video-1"},
                {"video_id": "video-2"},
            ]
        )
    except SupabaseAPIError as exc:
        message = str(exc)
    else:
        raise AssertionError("SupabaseAPIError was not raised")

    assert "Failed to upsert into yt_videos: 2 rows" in message
    assert "sample video_ids=['video-1', 'video-2']" in message
