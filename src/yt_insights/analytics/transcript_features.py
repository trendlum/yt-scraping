from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Any

import requests

from ..clients.http import build_retry_session
from ..constants import DEFAULT_TIMEOUT
from ..models import VideoFeatureRecord


LOGGER = logging.getLogger(__name__)
_PLAYER_RESPONSE_MARKER = re.compile(r"ytInitialPlayerResponse\s*=\s*")
_PREFERRED_LANGUAGES = ("en", "es")


@dataclass(slots=True)
class TranscriptFeatures:
    status: str
    language: str | None
    is_auto_generated: bool | None
    transcript_text: str | None


class TranscriptFeatureExtractor:
    def __init__(
        self,
        *,
        timeout: int = DEFAULT_TIMEOUT,
        session: requests.Session | None = None,
        preferred_languages: tuple[str, ...] = _PREFERRED_LANGUAGES,
        allow_auto_generated: bool = True,
    ) -> None:
        self.timeout = timeout
        self.session = session or build_retry_session()
        self.preferred_languages = preferred_languages
        self.allow_auto_generated = allow_auto_generated

    def extract_from_video_id(self, video_id: str) -> TranscriptFeatures:
        watch_url = f"https://www.youtube.com/watch?v={video_id}&hl=en&persist_hl=1"
        try:
            response = self.session.get(watch_url, timeout=self.timeout)
            response.raise_for_status()
        except requests.RequestException as exc:
            LOGGER.warning("Transcript page fetch failed for %s: %s", video_id, exc)
            return TranscriptFeatures(
                status="download_failed",
                language=None,
                is_auto_generated=None,
                transcript_text=None,
            )

        player_response = _extract_player_response(response.text)
        if player_response is None:
            return TranscriptFeatures(
                status="parse_failed",
                language=None,
                is_auto_generated=None,
                transcript_text=None,
            )

        caption_tracks = (
            player_response.get("captions", {})
            .get("playerCaptionsTracklistRenderer", {})
            .get("captionTracks", [])
        )
        if not caption_tracks:
            return TranscriptFeatures(
                status="no_captions",
                language=None,
                is_auto_generated=None,
                transcript_text=None,
            )

        chosen_track = self._choose_track(caption_tracks)
        if chosen_track is None:
            return TranscriptFeatures(
                status="no_captions",
                language=None,
                is_auto_generated=None,
                transcript_text=None,
            )

        transcript_text = self._download_track_transcript(chosen_track)
        if transcript_text is None:
            return TranscriptFeatures(
                status="download_failed",
                language=str(chosen_track.get("languageCode")) if chosen_track.get("languageCode") else None,
                is_auto_generated=bool(chosen_track.get("kind") == "asr"),
                transcript_text=None,
            )

        return TranscriptFeatures(
            status="complete",
            language=str(chosen_track.get("languageCode")) if chosen_track.get("languageCode") else None,
            is_auto_generated=bool(chosen_track.get("kind") == "asr"),
            transcript_text=transcript_text,
        )

    def _choose_track(self, caption_tracks: list[dict[str, Any]]) -> dict[str, Any] | None:
        candidates = [track for track in caption_tracks if isinstance(track, dict)]
        if not candidates:
            return None

        preferred: list[dict[str, Any]] = []
        for language in self.preferred_languages:
            preferred.extend(
                track
                for track in candidates
                if track.get("languageCode") == language
                and (self.allow_auto_generated or track.get("kind") != "asr")
            )
        if preferred:
            return preferred[0]

        non_auto = [track for track in candidates if track.get("kind") != "asr"]
        if non_auto:
            return non_auto[0]

        if self.allow_auto_generated:
            return candidates[0]

        return None

    def _download_track_transcript(self, track: dict[str, Any]) -> str | None:
        base_url = track.get("baseUrl")
        if not base_url:
            return None

        transcript_url = _ensure_query_param(str(base_url), "fmt", "json3")
        try:
            response = self.session.get(transcript_url, timeout=self.timeout)
            response.raise_for_status()
        except requests.RequestException as exc:
            LOGGER.warning("Transcript fetch failed: %s", exc)
            return None

        try:
            payload = response.json()
        except ValueError:
            try:
                payload = json.loads(response.text)
            except ValueError:
                return None

        return _flatten_transcript_payload(payload)


def enrich_transcript_features(
    feature_record: VideoFeatureRecord,
    extractor: TranscriptFeatureExtractor,
) -> VideoFeatureRecord:
    features = extractor.extract_from_video_id(feature_record.video_id)
    feature_record.transcript_status = features.status
    feature_record.transcript_language = features.language
    feature_record.transcript_is_auto_generated = features.is_auto_generated
    feature_record.transcript_text = features.transcript_text
    return feature_record


def _extract_player_response(html: str) -> dict[str, Any] | None:
    match = _PLAYER_RESPONSE_MARKER.search(html)
    if match is None:
        return None

    start = html.find("{", match.end())
    if start < 0:
        return None

    payload_text = _extract_balanced_json_object(html, start)
    if payload_text is None:
        return None

    try:
        return json.loads(payload_text)
    except ValueError:
        return None


def _extract_balanced_json_object(text: str, start_index: int) -> str | None:
    depth = 0
    in_string = False
    escape_next = False

    for index in range(start_index, len(text)):
        char = text[index]
        if in_string:
            if escape_next:
                escape_next = False
                continue
            if char == "\\":
                escape_next = True
                continue
            if char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start_index : index + 1]

    return None


def _flatten_transcript_payload(payload: dict[str, Any]) -> str | None:
    lines: list[str] = []
    for event in payload.get("events", []):
        if not isinstance(event, dict):
            continue
        segments = event.get("segs", [])
        if not isinstance(segments, list):
            continue
        parts: list[str] = []
        for segment in segments:
            if not isinstance(segment, dict):
                continue
            text = str(segment.get("utf8") or "")
            if text:
                parts.append(text)
        line = "".join(parts).strip()
        if line:
            lines.append(line)

    if not lines:
        return None

    return "\n".join(lines)


def _ensure_query_param(url: str, key: str, value: str) -> str:
    separator = "&" if "?" in url else "?"
    if re.search(rf"(?:[?&]){re.escape(key)}=", url):
        return re.sub(rf"([?&]){re.escape(key)}=[^&]*", rf"\1{key}={value}", url, count=1)
    return f"{url}{separator}{key}={value}"
