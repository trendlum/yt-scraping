from __future__ import annotations

import argparse
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests


YOUTUBE_API_BASE_URL = "https://www.googleapis.com/youtube/v3"
DEFAULT_TIMEOUT = 20
THUMBNAIL_PRIORITY = ("maxres", "standard", "high", "medium", "default")
SCRAPER_STATE_NAME = "youtube_channel_scraper"


class YouTubeAPIError(RuntimeError):
    """Raised when the YouTube Data API returns an error or invalid payload."""


class SupabaseAPIError(RuntimeError):
    """Raised when the Supabase REST API returns an error or invalid payload."""


def load_dotenv(dotenv_path: str | Path = ".env") -> None:
    path = Path(dotenv_path)
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _request_json(
    endpoint: str,
    params: dict[str, Any],
    timeout: int = DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    url = f"{YOUTUBE_API_BASE_URL}/{endpoint}"

    try:
        response = requests.get(url, params=params, timeout=timeout)
        response.raise_for_status()
    except requests.Timeout as exc:
        raise YouTubeAPIError(
            f"Timeout while calling {endpoint} with params={params}"
        ) from exc
    except requests.HTTPError as exc:
        detail = exc.response.text if exc.response is not None else str(exc)
        raise YouTubeAPIError(
            f"HTTP error while calling {endpoint}: {detail}"
        ) from exc
    except requests.RequestException as exc:
        raise YouTubeAPIError(f"Request failed while calling {endpoint}: {exc}") from exc

    try:
        payload = response.json()
    except ValueError as exc:
        raise YouTubeAPIError(f"Invalid JSON received from {endpoint}") from exc

    if "error" in payload:
        raise YouTubeAPIError(
            f"YouTube API error while calling {endpoint}: {payload['error']}"
        )

    return payload


def _supabase_headers(supabase_key: str) -> dict[str, str]:
    return {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
        "Content-Type": "application/json",
    }


def _supabase_request(
    method: str,
    supabase_url: str,
    supabase_key: str,
    path: str,
    *,
    params: dict[str, Any] | None = None,
    json_body: Any | None = None,
    extra_headers: dict[str, str] | None = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> Any:
    url = f"{supabase_url.rstrip('/')}/rest/v1/{path.lstrip('/')}"
    headers = _supabase_headers(supabase_key)
    if extra_headers:
        headers.update(extra_headers)

    try:
        response = requests.request(
            method=method,
            url=url,
            params=params,
            json=json_body,
            headers=headers,
            timeout=timeout,
        )
        response.raise_for_status()
    except requests.Timeout as exc:
        raise SupabaseAPIError(f"Timeout while calling Supabase path {path}") from exc
    except requests.HTTPError as exc:
        detail = exc.response.text if exc.response is not None else str(exc)
        raise SupabaseAPIError(f"HTTP error while calling Supabase path {path}: {detail}") from exc
    except requests.RequestException as exc:
        raise SupabaseAPIError(f"Request failed while calling Supabase path {path}: {exc}") from exc

    if not response.text.strip():
        return None

    try:
        return response.json()
    except ValueError as exc:
        raise SupabaseAPIError(f"Invalid JSON received from Supabase path {path}") from exc


def _pick_thumbnail_url(thumbnails: dict[str, Any] | None) -> str | None:
    if not thumbnails:
        return None

    for key in THUMBNAIL_PRIORITY:
        candidate = thumbnails.get(key)
        if isinstance(candidate, dict) and candidate.get("url"):
            return str(candidate["url"])

    return None


def _to_int_or_none(value: str | int | None) -> int | None:
    if value in (None, ""):
        return None

    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def _parse_duration_to_hms(duration: str | None) -> str | None:
    if not duration:
        return None

    match = re.fullmatch(
        r"P(?:(?P<days>\d+)D)?(?:T(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?(?:(?P<seconds>\d+)S)?)?",
        duration,
    )
    if not match:
        return None

    days = int(match.group("days") or 0)
    hours = int(match.group("hours") or 0)
    minutes = int(match.group("minutes") or 0)
    seconds = int(match.group("seconds") or 0)
    total_seconds = days * 86400 + hours * 3600 + minutes * 60 + seconds

    total_hours, remainder = divmod(total_seconds, 3600)
    total_minutes, remaining_seconds = divmod(remainder, 60)
    return f"{total_hours:02d}:{total_minutes:02d}:{remaining_seconds:02d}"


def get_channel_by_handle(
    api_key: str,
    channel_handle: str,
    timeout: int = DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    normalized_handle = channel_handle.lstrip("@")
    payload = _request_json(
        "channels",
        {
            "key": api_key,
            "part": "snippet,contentDetails",
            "forHandle": normalized_handle,
        },
        timeout=timeout,
    )

    items = payload.get("items", [])
    if not items:
        raise YouTubeAPIError(f"Channel not found for handle: {channel_handle}")

    return items[0]


def get_uploads_playlist_id(channel_data: dict[str, Any]) -> str:
    uploads_playlist_id = (
        channel_data.get("contentDetails", {})
        .get("relatedPlaylists", {})
        .get("uploads")
    )
    if not uploads_playlist_id:
        raise YouTubeAPIError("Uploads playlist ID not found in channel data")
    return str(uploads_playlist_id)


def get_latest_video_ids(
    api_key: str,
    uploads_playlist_id: str,
    limit: int | None,
    published_after: datetime | None = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> list[str]:
    video_ids: list[str] = []
    page_token: str | None = None
    max_items = limit if limit and limit > 0 else None

    while True:
        remaining = 50 if max_items is None else min(50, max_items - len(video_ids))
        if remaining <= 0:
            break

        params: dict[str, Any] = {
            "key": api_key,
            "part": "contentDetails,snippet",
            "playlistId": uploads_playlist_id,
            "maxResults": remaining,
        }
        if page_token:
            params["pageToken"] = page_token

        payload = _request_json("playlistItems", params, timeout=timeout)
        items = payload.get("items", [])
        reached_older_video = False

        for item in items:
            video_id = item.get("contentDetails", {}).get("videoId")
            published_at = _parse_datetime(item.get("contentDetails", {}).get("videoPublishedAt"))
            if not published_at:
                published_at = _parse_datetime(item.get("snippet", {}).get("publishedAt"))

            if published_after and published_at and published_at <= published_after:
                reached_older_video = True
                break

            if video_id:
                video_ids.append(str(video_id))
                if max_items is not None and len(video_ids) >= max_items:
                    break

        if reached_older_video:
            break
        if max_items is not None and len(video_ids) >= max_items:
            break

        page_token = payload.get("nextPageToken")
        if not page_token:
            break

    return video_ids


def get_videos_details(
    api_key: str,
    video_ids: list[str],
    timeout: int = DEFAULT_TIMEOUT,
) -> list[dict[str, Any]]:
    if not video_ids:
        return []

    videos_by_id: dict[str, dict[str, Any]] = {}

    for index in range(0, len(video_ids), 50):
        chunk = video_ids[index : index + 50]
        payload = _request_json(
            "videos",
            {
                "key": api_key,
                "part": "snippet,statistics,contentDetails",
                "id": ",".join(chunk),
                "maxResults": len(chunk),
            },
            timeout=timeout,
        )

        for item in payload.get("items", []):
            snippet = item.get("snippet", {})
            statistics = item.get("statistics", {})
            content_details = item.get("contentDetails", {})
            video_id = item.get("id")
            if not video_id:
                continue

            duration_iso = content_details.get("duration")
            videos_by_id[str(video_id)] = {
                "video_id": str(video_id),
                "title": snippet.get("title"),
                "channel_title": snippet.get("channelTitle"),
                "published_at": snippet.get("publishedAt"),
                "thumbnail_url": _pick_thumbnail_url(snippet.get("thumbnails")),
                "view_count": _to_int_or_none(statistics.get("viewCount")),
                "like_count": _to_int_or_none(statistics.get("likeCount")),
                "comment_count": _to_int_or_none(statistics.get("commentCount")),
                "duration": _parse_duration_to_hms(duration_iso),
                "duration_iso8601": duration_iso,
                "video_url": f"https://www.youtube.com/watch?v={video_id}",
            }

    return [videos_by_id[video_id] for video_id in video_ids if video_id in videos_by_id]


def scrape_channel_latest_videos(
    api_key: str,
    channel_handle: str,
    limit: int | None,
    published_after: datetime | None = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    channel_data = get_channel_by_handle(api_key, channel_handle, timeout=timeout)
    uploads_playlist_id = get_uploads_playlist_id(channel_data)
    video_ids = get_latest_video_ids(
        api_key,
        uploads_playlist_id,
        limit,
        published_after=published_after,
        timeout=timeout,
    )
    videos = get_videos_details(api_key, video_ids, timeout=timeout)

    return {
        "channel_id": channel_data.get("id"),
        "channel_name": channel_data.get("snippet", {}).get("title"),
        "uploads_playlist_id": uploads_playlist_id,
        "videos": videos,
    }


def get_supabase_channel_handles(
    supabase_url: str,
    supabase_key: str,
    timeout: int = DEFAULT_TIMEOUT,
) -> list[str]:
    payload = _supabase_request(
        "GET",
        supabase_url,
        supabase_key,
        "yt_channels",
        params={
            "select": "channel_handle",
            "is_active": "eq.true",
            "order": "id.asc",
        },
        timeout=timeout,
    )

    handles = [row["channel_handle"] for row in payload or [] if row.get("channel_handle")]
    if not handles:
        raise SupabaseAPIError("No active channel handles found in yt_channels")
    return handles


def get_last_scraper_run(
    supabase_url: str,
    supabase_key: str,
    scraper_name: str = SCRAPER_STATE_NAME,
    timeout: int = DEFAULT_TIMEOUT,
) -> datetime | None:
    payload = _supabase_request(
        "GET",
        supabase_url,
        supabase_key,
        "yt_scraper_state",
        params={
            "select": "scraper_name,last_run_at",
            "scraper_name": f"eq.{scraper_name}",
            "limit": 1,
        },
        timeout=timeout,
    )

    if not payload:
        return None

    return _parse_datetime(payload[0].get("last_run_at"))


def upsert_video_rows(
    supabase_url: str,
    supabase_key: str,
    rows: list[dict[str, Any]],
    timeout: int = DEFAULT_TIMEOUT,
) -> None:
    if not rows:
        return

    _supabase_request(
        "POST",
        supabase_url,
        supabase_key,
        "yt_videos",
        params={"on_conflict": "video_id"},
        json_body=rows,
        extra_headers={
            "Prefer": "resolution=merge-duplicates,return=minimal",
        },
        timeout=timeout,
    )


def update_scraper_state(
    supabase_url: str,
    supabase_key: str,
    executed_at: datetime,
    scraper_name: str = SCRAPER_STATE_NAME,
    timeout: int = DEFAULT_TIMEOUT,
) -> None:
    _supabase_request(
        "POST",
        supabase_url,
        supabase_key,
        "yt_scraper_state",
        params={"on_conflict": "scraper_name"},
        json_body=[
            {
                "scraper_name": scraper_name,
                "last_run_at": executed_at.isoformat(),
            }
        ],
        extra_headers={
            "Prefer": "resolution=merge-duplicates,return=minimal",
        },
        timeout=timeout,
    )


def build_video_rows(channel_result: dict[str, Any], fetched_at: datetime) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for video in channel_result.get("videos", []):
        rows.append(
            {
                "video_id": video["video_id"],
                "channel_handle": None,
                "title": video.get("title"),
                "published_at": video.get("published_at"),
                "thumbnail_url": video.get("thumbnail_url"),
                "view_count": video.get("view_count"),
                "like_count": video.get("like_count"),
                "comment_count": video.get("comment_count"),
                "duration": video.get("duration"),
                "duration_iso8601": video.get("duration_iso8601"),
                "video_url": video.get("video_url"),
                "fetched_at": fetched_at.isoformat(),
            }
        )
    return rows


def scrape_and_store_channels(
    api_key: str,
    supabase_url: str,
    supabase_key: str,
    limit: int | None,
    timeout: int = DEFAULT_TIMEOUT,
) -> list[dict[str, Any]]:
    run_started_at = datetime.now(timezone.utc)
    last_run_at = get_last_scraper_run(supabase_url, supabase_key, timeout=timeout)
    channel_handles = get_supabase_channel_handles(supabase_url, supabase_key, timeout=timeout)

    results: list[dict[str, Any]] = []
    video_rows: list[dict[str, Any]] = []

    for handle in channel_handles:
        channel_result = scrape_channel_latest_videos(
            api_key=api_key,
            channel_handle=handle,
            limit=limit,
            published_after=last_run_at,
            timeout=timeout,
        )
        for row in build_video_rows(channel_result, run_started_at):
            row["channel_handle"] = handle
            video_rows.append(row)
        results.append(channel_result)

    upsert_video_rows(supabase_url, supabase_key, video_rows, timeout=timeout)
    update_scraper_state(supabase_url, supabase_key, run_started_at, timeout=timeout)
    return results


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Fetch the latest videos from YouTube channels and store them in Supabase."
    )
    parser.add_argument("--api-key", help="YouTube Data API v3 key. Falls back to YT_API_KEY.")
    parser.add_argument("--channel-handle", help="Optional single YouTube channel handle.")
    parser.add_argument(
        "--limit",
        type=int,
        help="Maximum number of latest videos to fetch per channel. Omit to fetch all since last_run_at.",
    )
    parser.add_argument(
        "--supabase-url",
        help="Supabase project URL. Falls back to SUPABASE_URL.",
    )
    parser.add_argument(
        "--supabase-key",
        help="Supabase service role key. Falls back to SUPABASE_SERVICE_ROLE_KEY.",
    )
    parser.add_argument(
        "--output",
        help="Optional output JSON path. If omitted, the script prints to stdout.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT,
        help="HTTP timeout in seconds.",
    )
    return parser


if __name__ == "__main__":
    load_dotenv()
    parser = build_argument_parser()
    args = parser.parse_args()

    api_key = args.api_key or os.getenv("YT_API_KEY")
    if not api_key:
        raise SystemExit("Missing API key. Provide --api-key or set YT_API_KEY in .env")

    supabase_url = args.supabase_url or os.getenv("SUPABASE_URL")
    supabase_key = args.supabase_key or os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    try:
        if args.channel_handle:
            result: dict[str, Any] | list[dict[str, Any]] = scrape_channel_latest_videos(
                api_key=api_key,
                channel_handle=args.channel_handle,
                limit=args.limit,
                timeout=args.timeout,
            )
        else:
            if not supabase_url or not supabase_key:
                raise SystemExit(
                    "Missing Supabase credentials. Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in .env"
                )
            result = scrape_and_store_channels(
                api_key=api_key,
                supabase_url=supabase_url,
                supabase_key=supabase_key,
                limit=args.limit,
                timeout=args.timeout,
            )
    except (YouTubeAPIError, SupabaseAPIError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc

    output = json.dumps(result, ensure_ascii=False, indent=2)

    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
    else:
        print(output)
