from __future__ import annotations

import json
from pathlib import Path

from yt_insights.transcript_cli import TranscriptResult, TranscriptSegment, fetch_transcript, get_video_id, save_to_json


class FakeFetchedTranscript:
    def __init__(self, segments: list[dict]) -> None:
        self._segments = segments

    def to_raw_data(self) -> list[dict]:
        return self._segments


class FakeTranscript:
    def __init__(self, *, language_code: str, language: str, is_generated: bool, segments: list[dict]) -> None:
        self.language_code = language_code
        self.language = language
        self.is_generated = is_generated
        self._segments = segments

    def fetch(self) -> FakeFetchedTranscript:
        return FakeFetchedTranscript(self._segments)


class FakeTranscriptList:
    def __init__(self, transcripts: list[FakeTranscript]) -> None:
        self._transcripts = transcripts

    def find_transcript(self, languages: list[str]) -> FakeTranscript:
        for transcript in self._transcripts:
            if transcript.language_code in languages:
                return transcript
        raise NoTranscriptFound()

    def __iter__(self):
        return iter(self._transcripts)


class FakeApi:
    def __init__(self, transcript_list: FakeTranscriptList) -> None:
        self.transcript_list = transcript_list

    def list(self, video_id: str) -> FakeTranscriptList:
        return self.transcript_list


class NoTranscriptFound(Exception):
    pass


def test_get_video_id_extracts_from_standard_and_short_urls() -> None:
    assert get_video_id("https://www.youtube.com/watch?v=abc123DEF45&t=10s") == "abc123DEF45"
    assert get_video_id("https://youtu.be/abc123DEF45") == "abc123DEF45"
    assert get_video_id("abc123DEF45") == "abc123DEF45"


def test_fetch_transcript_prefers_english_when_available() -> None:
    api = FakeApi(
        FakeTranscriptList(
            [
                FakeTranscript(
                    language_code="es",
                    language="Spanish",
                    is_generated=False,
                    segments=[{"start": 0.0, "duration": 1.0, "text": "Hola"}],
                ),
                FakeTranscript(
                    language_code="en",
                    language="English",
                    is_generated=True,
                    segments=[
                        {"start": 0.0, "duration": 1.0, "text": "Hello"},
                        {"start": 1.0, "duration": 1.0, "text": "world"},
                    ],
                ),
            ]
        )
    )

    result = fetch_transcript("abc123DEF45", api=api)

    assert result.language_code == "en"
    assert result.full_text == "Hello world"
    assert [segment.text for segment in result.segments] == ["Hello", "world"]


def test_fetch_transcript_falls_back_to_any_available_language_when_english_is_missing() -> None:
    api = FakeApi(
        FakeTranscriptList(
            [
                FakeTranscript(
                    language_code="fr",
                    language="French",
                    is_generated=False,
                    segments=[{"start": 0.0, "duration": 1.0, "text": "Bonjour"}],
                )
            ]
        )
    )

    result = fetch_transcript("abc123DEF45", api=api)

    assert result.language_code == "fr"
    assert result.full_text == "Bonjour"


def test_save_to_json_writes_expected_payload(tmp_path: Path) -> None:
    result = TranscriptResult(
        video_id="abc123DEF45",
        language_code="en",
        language="English",
        is_generated=False,
        full_text="Hello world",
        segments=[
            TranscriptSegment(start=0.0, duration=1.0, text="Hello"),
            TranscriptSegment(start=1.0, duration=1.0, text="world"),
        ],
    )

    output = save_to_json(result, tmp_path / "abc123DEF45_transcript.json")
    payload = json.loads(output.read_text(encoding="utf-8"))

    assert payload["video_id"] == "abc123DEF45"
    assert payload["full_text"] == "Hello world"
    assert payload["segments"][0]["text"] == "Hello"
