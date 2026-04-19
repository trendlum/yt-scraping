from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import cv2
import numpy as np

from yt_insights.analytics.thumbnail_features import ThumbnailImageFeatures

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from thumbnail_test import load_image_from_input, main


def test_load_image_from_input_reads_local_file(tmp_path: Path) -> None:
    image = np.full((16, 16, 3), 255, dtype=np.uint8)
    image_path = tmp_path / "thumb.jpg"
    cv2.imwrite(str(image_path), image)

    image_bytes, source = load_image_from_input(str(image_path), timeout=1)

    assert source == str(image_path)
    assert len(image_bytes) > 0


def test_main_prints_thumbnail_features_for_local_image(tmp_path: Path, capsys) -> None:
    image = np.full((16, 16, 3), 255, dtype=np.uint8)
    image_path = tmp_path / "thumb.jpg"
    cv2.imwrite(str(image_path), image)

    dummy_features = ThumbnailImageFeatures(
        status="complete",
        ocr_status="not_available",
        has_face=False,
        face_count=0,
        has_thumbnail_text=False,
        estimated_thumbnail_text_tokens=0,
        thumbnail_text=None,
        thumbnail_text_confidence=None,
        dominant_colors=["#ffffff"],
        composition_type="balanced",
        contains_chart=False,
        contains_map=False,
        visual_style="simple",
    )

    with patch("thumbnail_test.ThumbnailFeatureExtractor") as mocked_extractor_cls:
        mocked_extractor = mocked_extractor_cls.return_value
        mocked_extractor.extract_from_bytes.return_value = dummy_features

        exit_code = main([str(image_path)])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "source:" in captured.out
    assert "has_thumbnail_text: False" in captured.out
    assert "thumbnail_text: None" in captured.out
