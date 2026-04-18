from __future__ import annotations

from yt_insights.analytics.transcript_features import TranscriptFeatureExtractor


class FakeResponse:
    def __init__(self, *, text: str, json_data: dict | None = None, status_code: int = 200) -> None:
        self.text = text
        self._json_data = json_data
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"status {self.status_code}")

    def json(self):
        if self._json_data is None:
            raise ValueError("invalid json")
        return self._json_data


class FakeSession:
    def __init__(self, responses: dict[str, FakeResponse]) -> None:
        self.responses = responses
        self.requested_urls: list[str] = []

    def get(self, url: str, timeout: int):
        self.requested_urls.append(url)
        for key, response in self.responses.items():
            if key in url:
                return response
        raise RuntimeError(f"unexpected url: {url}")


def test_transcript_extractor_reads_caption_tracks_and_flattens_json3_payload() -> None:
    html = """
        <html>
        <script>
        var ytInitialPlayerResponse = {"captions":{"playerCaptionsTracklistRenderer":{"captionTracks":[{"baseUrl":"https://example.com/captions?id=123","languageCode":"en","kind":"asr"}]}}};
        </script>
        </html>
    """
    transcript_payload = {
        "events": [
            {"segs": [{"utf8": "Hello "}, {"utf8": "world"}]},
            {"segs": [{"utf8": "This is a test"}]},
        ]
    }
    session = FakeSession(
        {
            "watch?v=video-1": FakeResponse(text=html),
            "example.com/captions": FakeResponse(text="", json_data=transcript_payload),
        }
    )
    extractor = TranscriptFeatureExtractor(session=session)

    features = extractor.extract_from_video_id("video-1")

    assert features.status == "complete"
    assert features.language == "en"
    assert features.is_auto_generated is True
    assert features.transcript_text == "Hello world\nThis is a test"
    assert len(session.requested_urls) == 2


def test_transcript_extractor_returns_no_captions_when_page_has_none() -> None:
    html = """
        <html>
        <script>
        var ytInitialPlayerResponse = {"captions":{}};
        </script>
        </html>
    """
    session = FakeSession({"watch?v=video-2": FakeResponse(text=html)})
    extractor = TranscriptFeatureExtractor(session=session)

    features = extractor.extract_from_video_id("video-2")

    assert features.status == "no_captions"
    assert features.transcript_text is None
