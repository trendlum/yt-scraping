from __future__ import annotations

import cv2
import numpy as np

from yt_insights.analytics.thumbnail_features import ThumbnailFeatureExtractor


class FakeOCRReader:
    def __init__(self, detections):
        self.detections = detections

    def readtext(self, image, detail: int = 1, paragraph: bool = False):
        return self.detections


def _build_text_thumbnail() -> np.ndarray:
    image = np.full((180, 320, 3), 255, dtype=np.uint8)
    image[:, :160] = (30, 30, 220)
    cv2.rectangle(image, (20, 110), (300, 165), (0, 0, 0), -1)
    cv2.putText(
        image,
        "BIG MOVE",
        (28, 148),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.1,
        (255, 255, 255),
        3,
        cv2.LINE_AA,
    )
    return image


def test_thumbnail_extractor_detects_text_regions_and_colors() -> None:
    extractor = ThumbnailFeatureExtractor(
        ocr_reader=FakeOCRReader(
            [
                ([[0, 0], [1, 0], [1, 1], [0, 1]], "BIG", 0.93),
                ([[0, 0], [1, 0], [1, 1], [0, 1]], "MOVE", 0.87),
            ]
        )
    )
    features = extractor.extract_from_image(_build_text_thumbnail())

    assert features.status == "complete"
    assert features.ocr_status == "extracted"
    assert features.has_thumbnail_text is True
    assert features.estimated_thumbnail_text_tokens is not None
    assert features.estimated_thumbnail_text_tokens >= 1
    assert features.thumbnail_text == "BIG MOVE"
    assert features.thumbnail_text_confidence == 0.9
    assert features.dominant_colors is not None
    assert len(features.dominant_colors) == 3
    assert all(color.startswith("#") for color in features.dominant_colors)
    assert features.visual_style in {"graphic", "mixed", "simple"}


def test_thumbnail_extractor_marks_no_text_when_ocr_finds_nothing() -> None:
    extractor = ThumbnailFeatureExtractor(ocr_reader=FakeOCRReader([]))
    features = extractor.extract_from_image(_build_text_thumbnail())

    assert features.status == "complete"
    assert features.ocr_status == "no_text"
    assert features.has_thumbnail_text is False
    assert features.estimated_thumbnail_text_tokens == 0
    assert features.thumbnail_text is None
    assert features.thumbnail_text_confidence is None


def test_thumbnail_extractor_handles_invalid_bytes() -> None:
    extractor = ThumbnailFeatureExtractor()
    features = extractor.extract_from_bytes(b"not-an-image")

    assert features.status == "decode_failed"
    assert features.ocr_status == "decode_failed"
    assert features.has_thumbnail_text is None
    assert features.thumbnail_text is None
    assert features.thumbnail_text_confidence is None


def test_thumbnail_extractor_marks_ocr_not_available_when_disabled() -> None:
    extractor = ThumbnailFeatureExtractor(enable_ocr=False)
    features = extractor.extract_from_image(_build_text_thumbnail())

    assert features.status == "complete"
    assert features.ocr_status == "not_available"
    assert features.thumbnail_text is None
    assert features.thumbnail_text_confidence is None
