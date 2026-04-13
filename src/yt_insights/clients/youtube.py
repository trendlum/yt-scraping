from __future__ import annotations

from datetime import datetime
from typing import Any

import requests

from ..constants import DEFAULT_TIMEOUT, YOUTUBE_API_BASE_URL
from ..exceptions import YouTubeAPIError
from ..models import ChannelScrapeResult, VideoRecord, parse_datetime
from .http import build_retry_session


class YouTubeClient:
    def __init__(
        self,
        api_key: str,
        *,
        timeout: int = DEFAULT_TIMEOUT,
        session: requests.Session | None = None,
    ) -> None:
        self.api_key = api_key
        self.timeout = timeout
        self.session = session or build_retry_session()

    def _request_json(self, endpoint: str, params: dict[str, Any]) -> dict[str, Any]:
        url = f"{YOUTUBE_API_BASE_URL}/{endpoint}"

        try:
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
        except requests.Timeout as exc:
            raise YouTubeAPIError(
                f"Timeout while calling {endpoint} with params={params}"
            ) from exc
        except requests.HTTPError as exc:
            detail = exc.response.text if exc.response is not None else str(exc)
            raise YouTubeAPIError(f"HTTP error while calling {endpoint}: {detail}") from exc
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

    def get_channel_by_handle(self, channel_handle: str) -> dict[str, Any]:
        normalized_handle = channel_handle.lstrip("@")
        payload = self._request_json(
            "channels",
            {
                "key": self.api_key,
                "part": "snippet,contentDetails",
                "forHandle": normalized_handle,
            },
        )

        items = payload.get("items", [])
        if not items:
            raise YouTubeAPIError(f"Channel not found for handle: {channel_handle}")

        return items[0]

    @staticmethod
    def get_uploads_playlist_id(channel_data: dict[str, Any]) -> str:
        uploads_playlist_id = (
            channel_data.get("contentDetails", {})
            .get("relatedPlaylists", {})
            .get("uploads")
        )
        if not uploads_playlist_id:
            raise YouTubeAPIError("Uploads playlist ID not found in channel data")
        return str(uploads_playlist_id)

    def list_upload_video_ids(
        self,
        uploads_playlist_id: str,
        *,
        limit: int | None,
        published_after: datetime | None = None,
    ) -> list[str]:
        video_ids: list[str] = []
        page_token: str | None = None
        max_items = limit if limit and limit > 0 else None

        while True:
            remaining = 50 if max_items is None else min(50, max_items - len(video_ids))
            if remaining <= 0:
                break

            params: dict[str, Any] = {
                "key": self.api_key,
                "part": "contentDetails,snippet",
                "playlistId": uploads_playlist_id,
                "maxResults": remaining,
            }
            if page_token:
                params["pageToken"] = page_token

            payload = self._request_json("playlistItems", params)
            items = payload.get("items", [])
            reached_older_video = False

            for item in items:
                video_id = item.get("contentDetails", {}).get("videoId")
                published_at = parse_datetime(
                    item.get("contentDetails", {}).get("videoPublishedAt")
                )
                if not published_at:
                    published_at = parse_datetime(item.get("snippet", {}).get("publishedAt"))

                if published_after and published_at and published_at <= published_after:
                    reached_older_video = True
                    break

                if video_id:
                    video_ids.append(str(video_id))
                    if max_items is not None and len(video_ids) >= max_items:
                        break

            if reached_older_video or (max_items is not None and len(video_ids) >= max_items):
                break

            page_token = payload.get("nextPageToken")
            if not page_token:
                break

        return video_ids

    def get_videos_details(self, video_ids: list[str]) -> list[VideoRecord]:
        if not video_ids:
            return []

        videos_by_id: dict[str, VideoRecord] = {}
        for index in range(0, len(video_ids), 50):
            chunk = video_ids[index : index + 50]
            payload = self._request_json(
                "videos",
                {
                    "key": self.api_key,
                    "part": "snippet,statistics,contentDetails",
                    "id": ",".join(chunk),
                    "maxResults": len(chunk),
                },
            )

            for item in payload.get("items", []):
                record = VideoRecord.from_api_item(item)
                if record is not None:
                    videos_by_id[record.video_id] = record

        return [videos_by_id[video_id] for video_id in video_ids if video_id in videos_by_id]

    def scrape_channel_latest_videos(
        self,
        channel_handle: str,
        *,
        limit: int | None,
        published_after: datetime | None = None,
    ) -> ChannelScrapeResult:
        channel_data = self.get_channel_by_handle(channel_handle)
        uploads_playlist_id = self.get_uploads_playlist_id(channel_data)
        video_ids = self.list_upload_video_ids(
            uploads_playlist_id,
            limit=limit,
            published_after=published_after,
        )
        videos = self.get_videos_details(video_ids)

        return ChannelScrapeResult(
            channel_handle=channel_handle,
            channel_id=channel_data.get("id"),
            channel_name=channel_data.get("snippet", {}).get("title"),
            uploads_playlist_id=uploads_playlist_id,
            videos=videos,
        )
