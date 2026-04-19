from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Sequence
from urllib.parse import parse_qs, urlparse

import requests


_YOUTUBE_HOSTNAMES = ("youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be")


@dataclass(slots=True, frozen=True)
class TranscriptSegment:
    start: float
    duration: float
    text: str


@dataclass(slots=True, frozen=True)
class TranscriptResult:
    video_id: str
    language_code: str | None
    language: str | None
    is_generated: bool | None
    full_text: str
    segments: list[TranscriptSegment]


class TranscriptError(RuntimeError):
    """Base error for transcript fetch failures."""


class VideoUnavailableError(TranscriptError):
    """Raised when YouTube reports that the video cannot be accessed."""


class TranscriptNotAvailableError(TranscriptError):
    """Raised when no transcript exists for the requested video."""


class TranscriptNetworkError(TranscriptError):
    """Raised when the underlying network request fails."""


class TranscriptRequestBlockedError(TranscriptNetworkError):
    """Raised when YouTube blocks transcript requests from the current IP."""


class TranscriptIpBlockedError(TranscriptNetworkError):
    """Raised when YouTube blocks the current IP from transcript access."""


class TranscriptDependencyError(TranscriptError):
    """Raised when the youtube-transcript-api dependency is missing."""


def get_video_id(value: str) -> str:
    candidate = value.strip()
    if not candidate:
        raise ValueError("A video URL or video_id is required.")

    if "://" not in candidate:
        return candidate

    parsed = urlparse(candidate)
    hostname = (parsed.hostname or "").lower()
    if not any(hostname == allowed or hostname.endswith(f".{allowed}") for allowed in _YOUTUBE_HOSTNAMES):
        raise ValueError("Input must be a YouTube video URL or a raw video_id.")

    if hostname.endswith("youtu.be"):
        video_id = _first_path_segment(parsed.path)
        if video_id:
            return video_id
    else:
        query = parse_qs(parsed.query)
        video_id = _first_non_empty(query.get("v", []))
        if video_id:
            return video_id

        path_segments = [segment for segment in parsed.path.split("/") if segment]
        for index, segment in enumerate(path_segments):
            if segment in {"embed", "shorts", "live", "v"} and index + 1 < len(path_segments):
                return path_segments[index + 1]

    raise ValueError("Could not extract a video_id from the provided YouTube URL.")


def fetch_transcript(video_id: str, api: Any | None = None) -> TranscriptResult:
    youtube_api = api or _create_youtube_transcript_api()

    try:
        transcript = _select_transcript(youtube_api, video_id)
        fetched = transcript.fetch()
    except VideoUnavailableError:
        raise
    except TranscriptNotAvailableError:
        raise
    except requests.RequestException as exc:
        raise TranscriptNetworkError(f"Network error while fetching transcript for {video_id}: {exc}") from exc
    except Exception as exc:  # pragma: no cover - library-specific failures
        if _is_youtube_transcript_exception(exc, "VideoUnavailable"):
            raise VideoUnavailableError(f"Video unavailable: {video_id}") from exc
        if _is_youtube_transcript_exception(exc, "TranscriptsDisabled") or _is_youtube_transcript_exception(
            exc, "NoTranscriptFound"
        ):
            raise TranscriptNotAvailableError(f"No transcript available for video {video_id}") from exc
        if _is_youtube_transcript_exception(exc, "RequestBlocked"):
            raise TranscriptRequestBlockedError(
                f"Transcript request blocked for {video_id}: {exc}"
            ) from exc
        if _is_youtube_transcript_exception(exc, "IpBlocked"):
            raise TranscriptIpBlockedError(
                f"Transcript IP blocked for {video_id}: {exc}"
            ) from exc
        raise

    segments = _segments_from_fetched_transcript(fetched)
    full_text = _join_segments(segments)

    return TranscriptResult(
        video_id=video_id,
        language_code=getattr(transcript, "language_code", None),
        language=getattr(transcript, "language", None),
        is_generated=getattr(transcript, "is_generated", None),
        full_text=full_text,
        segments=segments,
    )


def save_to_json(result: TranscriptResult, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "video_id": result.video_id,
        "language_code": result.language_code,
        "language": result.language,
        "is_generated": result.is_generated,
        "full_text": result.full_text,
        "segments": [asdict(segment) for segment in result.segments],
    }
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return output_path


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Fetch a YouTube transcript and export it to JSON.")
    parser.add_argument("video_url_or_id", help="YouTube video URL or video_id.")
    parser.add_argument(
        "--output",
        help="Optional output path. Defaults to <video_id>_transcript.json in the current directory.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        help="Python logging level. Example: INFO, DEBUG, WARNING.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_argument_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=getattr(logging, str(args.log_level).upper(), logging.INFO),
        format="%(levelname)s: %(message)s",
    )

    try:
        video_id = get_video_id(args.video_url_or_id)
        transcript = fetch_transcript(video_id)
        output_path = Path(args.output) if args.output else Path(f"{video_id}_transcript.json")
        save_to_json(transcript, output_path)
        print(_format_console_output(transcript, output_path))
    except TranscriptDependencyError as exc:
        raise SystemExit(str(exc)) from exc
    except VideoUnavailableError as exc:
        raise SystemExit(str(exc)) from exc
    except TranscriptNotAvailableError as exc:
        raise SystemExit(str(exc)) from exc
    except TranscriptNetworkError as exc:
        raise SystemExit(str(exc)) from exc
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    return 0


def _create_youtube_transcript_api() -> Any:
    return create_youtube_transcript_api(None)


def create_youtube_transcript_api(http_client: Any | None = None) -> Any:
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
    except ImportError as exc:  # pragma: no cover - dependency issue is environment-specific
        raise TranscriptDependencyError(
            "Missing dependency: youtube-transcript-api. Install it with `pip install youtube-transcript-api`."
        ) from exc

    if http_client is None:
        return YouTubeTranscriptApi()
    return YouTubeTranscriptApi(http_client=http_client)


def _select_transcript(api: Any, video_id: str) -> Any:
    transcript_list = api.list(video_id)
    try:
        return transcript_list.find_transcript(["en"])
    except Exception as exc:
        if not _is_youtube_transcript_exception(exc, "NoTranscriptFound"):
            raise

    transcript = next(iter(transcript_list), None)
    if transcript is None:
        raise TranscriptNotAvailableError(f"No transcript available for video {video_id}")
    return transcript


def _segments_from_fetched_transcript(fetched: Any) -> list[TranscriptSegment]:
    if hasattr(fetched, "to_raw_data"):
        raw_segments = fetched.to_raw_data()
    else:  # pragma: no cover - compatibility fallback
        raw_segments = [
            {
                "start": getattr(segment, "start", 0.0),
                "duration": getattr(segment, "duration", 0.0),
                "text": getattr(segment, "text", ""),
            }
            for segment in fetched
        ]

    segments: list[TranscriptSegment] = []
    for segment in raw_segments or []:
        text = str(segment.get("text", "")).strip()
        if not text:
            continue
        segments.append(
            TranscriptSegment(
                start=float(segment.get("start", 0.0)),
                duration=float(segment.get("duration", 0.0)),
                text=text,
            )
        )
    return segments


def _join_segments(segments: list[TranscriptSegment]) -> str:
    return " ".join(segment.text for segment in segments).strip()


def _format_console_output(result: TranscriptResult, output_path: Path) -> str:
    lines = [
        f"Video ID: {result.video_id}",
        f"Language: {result.language or 'unknown'} ({result.language_code or 'unknown'})",
        f"Generated: {result.is_generated}",
        f"Saved to: {output_path}",
        "",
        "Full transcript:",
        result.full_text or "[empty]",
        "",
        "Segments:",
    ]

    for index, segment in enumerate(result.segments, start=1):
        lines.append(
            f"{index:03d}. start={segment.start:.3f}s duration={segment.duration:.3f}s text={segment.text}"
        )

    if not result.segments:
        lines.append("[no segments]")

    return "\n".join(lines)


def _first_non_empty(values: list[str]) -> str | None:
    for value in values:
        if value:
            return value
    return None


def _first_path_segment(path: str) -> str | None:
    segments = [segment for segment in path.split("/") if segment]
    return segments[0] if segments else None


def _is_youtube_transcript_exception(exc: Exception, name: str) -> bool:
    return exc.__class__.__name__ == name


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
