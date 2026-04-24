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


class _RecordingClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict | None]] = []

    def request(self, method, path, *, params=None, json_body=None, extra_headers=None):
        self.calls.append((method, path, params))
        if method == "GET":
            video_filter = params.get("video_id", "") if params else ""
            ids = [
                part.strip('"')
                for part in video_filter.removeprefix("in.(").removesuffix(")").split(",")
                if part
            ]
            return [{"video_id": video_id} for video_id in ids]
        return None


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


def test_supabase_repository_chunks_large_video_id_filters() -> None:
    client = _RecordingClient()
    repository = SupabaseRepository(client)
    video_ids = [f"video-{index}" for index in range(101)]

    rows = repository.get_current_video_rows(video_ids)

    assert len(rows) == 101
    get_calls = [call for call in client.calls if call[0] == "GET" and call[1] == "yt_videos"]
    assert len(get_calls) == 3
    assert all("in.(" in (params or {}).get("video_id", "") for _, _, params in get_calls)


def test_supabase_repository_chunks_large_topic_deletes() -> None:
    client = _RecordingClient()
    repository = SupabaseRepository(client)
    topics_by_video_id = {f"video-{index}": ["topic-a"] for index in range(101)}

    repository.replace_video_topics(topics_by_video_id)

    delete_calls = [call for call in client.calls if call[0] == "DELETE" and call[1] == "yt_video_topics"]
    assert len(delete_calls) == 3
    assert all("in.(" in (params or {}).get("video_id", "") for _, _, params in delete_calls)
