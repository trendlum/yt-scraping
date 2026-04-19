from __future__ import annotations

import copy
import logging
import re
from dataclasses import dataclass
from typing import Any, Protocol

import cv2
import numpy as np
import requests

from ..constants import DEFAULT_TIMEOUT
from ..models import VideoFeatureRecord
from ..clients.http import build_retry_session

try:
    import easyocr
except ImportError:  # pragma: no cover
    easyocr = None


LOGGER = logging.getLogger(__name__)
_THUMBNAIL_WORD_RE = re.compile(r"[A-Za-z0-9']+")


class OCRReader(Protocol):
    def readtext(self, image: Any, detail: int = 1, paragraph: bool = False) -> list[Any]:
        ...


@dataclass(slots=True)
class ThumbnailImageFeatures:
    status: str
    ocr_status: str
    has_face: bool | None
    face_count: int | None
    has_thumbnail_text: bool | None
    estimated_thumbnail_text_tokens: int | None
    thumbnail_text: str | None
    thumbnail_text_confidence: float | None
    dominant_colors: list[str] | None
    composition_type: str | None
    contains_chart: bool | None
    contains_map: bool | None
    visual_style: str | None


class ThumbnailFeatureExtractor:
    def __init__(
        self,
        *,
        timeout: int = DEFAULT_TIMEOUT,
        session: requests.Session | None = None,
        ocr_reader: OCRReader | None = None,
        enable_ocr: bool = True,
        ocr_languages: tuple[str, ...] = ("en", "es"),
    ) -> None:
        self.timeout = timeout
        self.session = session or build_retry_session()
        self._cache: dict[str, ThumbnailImageFeatures] = {}
        self._ocr_reader = ocr_reader
        self._ocr_available = enable_ocr
        self._ocr_languages = list(ocr_languages)
        self._ocr_init_attempted = ocr_reader is not None
        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        self.face_cascade = cv2.CascadeClassifier(cascade_path)

    def extract_from_url(self, thumbnail_url: str | None) -> ThumbnailImageFeatures:
        if not thumbnail_url:
            return ThumbnailImageFeatures(
                status="no_thumbnail",
                ocr_status="no_thumbnail",
                has_face=None,
                face_count=None,
                has_thumbnail_text=None,
                estimated_thumbnail_text_tokens=None,
                thumbnail_text=None,
                thumbnail_text_confidence=None,
                dominant_colors=None,
                composition_type=None,
                contains_chart=None,
                contains_map=None,
                visual_style=None,
            )

        cached = self._cache.get(thumbnail_url)
        if cached is not None:
            return copy.deepcopy(cached)

        try:
            response = self.session.get(thumbnail_url, timeout=self.timeout)
            response.raise_for_status()
        except requests.RequestException as exc:
            LOGGER.warning("Thumbnail download failed for %s: %s", thumbnail_url, exc)
            features = ThumbnailImageFeatures(
                status="download_failed",
                ocr_status="download_failed",
                has_face=None,
                face_count=None,
                has_thumbnail_text=None,
                estimated_thumbnail_text_tokens=None,
                thumbnail_text=None,
                thumbnail_text_confidence=None,
                dominant_colors=None,
                composition_type=None,
                contains_chart=None,
                contains_map=None,
                visual_style=None,
            )
            self._cache[thumbnail_url] = features
            return copy.deepcopy(features)

        features = self.extract_from_bytes(response.content)
        self._cache[thumbnail_url] = features
        return copy.deepcopy(features)

    def extract_from_bytes(self, image_bytes: bytes) -> ThumbnailImageFeatures:
        decoded = cv2.imdecode(np.frombuffer(image_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)
        if decoded is None:
            return ThumbnailImageFeatures(
                status="decode_failed",
                ocr_status="decode_failed",
                has_face=None,
                face_count=None,
                has_thumbnail_text=None,
                estimated_thumbnail_text_tokens=None,
                thumbnail_text=None,
                thumbnail_text_confidence=None,
                dominant_colors=None,
                composition_type=None,
                contains_chart=None,
                contains_map=None,
                visual_style=None,
            )
        return self.extract_from_image(decoded)

    def extract_from_image(self, image: np.ndarray) -> ThumbnailImageFeatures:
        resized = _resize_for_analysis(image)
        face_count = _detect_faces(resized, self.face_cascade)
        thumbnail_text, thumbnail_text_confidence, ocr_status = self._extract_thumbnail_text(image)
        has_text = thumbnail_text is not None
        if not has_text:
            thumbnail_text = None
            thumbnail_text_confidence = None
            estimated_tokens = 0
        else:
            estimated_tokens = len(_THUMBNAIL_WORD_RE.findall(thumbnail_text))
        dominant_colors = _extract_dominant_colors(resized)
        composition_type = _estimate_composition(resized)
        contains_chart = _detect_chart_like_layout(resized, has_text, face_count)
        contains_map = _detect_map_like_layout(resized, face_count, has_text)
        visual_style = _classify_visual_style(resized, has_text, face_count, contains_chart)

        return ThumbnailImageFeatures(
            status="complete",
            ocr_status=ocr_status,
            has_face=face_count > 0,
            face_count=face_count,
            has_thumbnail_text=has_text,
            estimated_thumbnail_text_tokens=estimated_tokens,
            thumbnail_text=thumbnail_text,
            thumbnail_text_confidence=thumbnail_text_confidence,
            dominant_colors=dominant_colors,
            composition_type=composition_type,
            contains_chart=contains_chart,
            contains_map=contains_map,
            visual_style=visual_style,
        )

    def _extract_thumbnail_text(
        self,
        image: np.ndarray,
    ) -> tuple[str | None, float | None, str]:
        reader = self._get_ocr_reader()
        if reader is None:
            return None, None, "not_available"

        prepared = _prepare_image_for_ocr(image)
        try:
            detections = reader.readtext(prepared, detail=1, paragraph=False)
        except Exception as exc:  # pragma: no cover
            LOGGER.warning("Thumbnail OCR failed: %s", exc)
            return None, None, "failed"

        texts: list[str] = []
        confidences: list[float] = []
        for detection in detections:
            if not isinstance(detection, (list, tuple)) or len(detection) < 3:
                continue
            text = str(detection[1]).strip()
            if not text:
                continue
            texts.append(text)
            confidence = _to_confidence(detection[2])
            if confidence is not None:
                confidences.append(confidence)

        if not texts:
            return None, None, "no_text"

        normalized_text = _normalize_ocr_text(texts)
        if not normalized_text:
            return None, None, "no_text"
        average_confidence = round(sum(confidences) / len(confidences), 4) if confidences else None
        return normalized_text, average_confidence, "extracted"

    def _get_ocr_reader(self) -> OCRReader | None:
        if not self._ocr_available:
            return None
        if self._ocr_reader is not None:
            return self._ocr_reader
        if self._ocr_init_attempted:
            return None

        self._ocr_init_attempted = True
        if easyocr is None:
            LOGGER.warning("easyocr is not installed; thumbnail OCR disabled")
            self._ocr_available = False
            return None

        try:
            self._ocr_reader = easyocr.Reader(self._ocr_languages, gpu=False, verbose=False)
        except Exception as exc:  # pragma: no cover
            LOGGER.warning("easyocr initialization failed; thumbnail OCR disabled: %s", exc)
            self._ocr_available = False
            return None
        return self._ocr_reader


def enrich_thumbnail_features(
    feature_record: VideoFeatureRecord,
    extractor: ThumbnailFeatureExtractor,
) -> VideoFeatureRecord:
    features = extractor.extract_from_url(feature_record.source_thumbnail_url)
    feature_record.thumbnail_feature_status = features.status
    feature_record.thumbnail_ocr_status = features.ocr_status
    feature_record.has_face = features.has_face
    feature_record.face_count = features.face_count
    feature_record.has_thumbnail_text = features.has_thumbnail_text
    feature_record.estimated_thumbnail_text_tokens = features.estimated_thumbnail_text_tokens
    feature_record.thumbnail_text = features.thumbnail_text
    feature_record.thumbnail_text_confidence = features.thumbnail_text_confidence
    feature_record.dominant_colors = features.dominant_colors
    feature_record.composition_type = features.composition_type
    feature_record.contains_chart = features.contains_chart
    feature_record.contains_map = features.contains_map
    feature_record.visual_style = features.visual_style
    return feature_record


def _resize_for_analysis(image: np.ndarray, width: int = 320) -> np.ndarray:
    current_height, current_width = image.shape[:2]
    if current_width <= width:
        return image
    ratio = width / float(current_width)
    resized_height = max(1, int(current_height * ratio))
    return cv2.resize(image, (width, resized_height), interpolation=cv2.INTER_AREA)


def _prepare_image_for_ocr(image: np.ndarray, width: int = 640) -> np.ndarray:
    resized = _resize_for_analysis(image, width=width)
    grayscale = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
    normalized = cv2.normalize(grayscale, None, 0, 255, cv2.NORM_MINMAX)
    return cv2.cvtColor(normalized, cv2.COLOR_GRAY2RGB)


def _detect_faces(image: np.ndarray, face_cascade: cv2.CascadeClassifier) -> int:
    if face_cascade.empty():
        return 0

    grayscale = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    equalized = cv2.equalizeHist(grayscale)
    faces = face_cascade.detectMultiScale(
        equalized,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(24, 24),
    )
    return int(len(faces))


def _extract_dominant_colors(image: np.ndarray, top_k: int = 3) -> list[str]:
    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    reduced = cv2.resize(rgb, (64, 64), interpolation=cv2.INTER_AREA)
    quantized = ((reduced // 64) * 64 + 32).reshape(-1, 3)
    colors, counts = np.unique(quantized, axis=0, return_counts=True)
    top_indices = np.argsort(counts)[::-1][:top_k]
    dominant: list[str] = []
    for index in top_indices:
        red, green, blue = [int(value) for value in colors[index]]
        dominant.append(f"#{red:02x}{green:02x}{blue:02x}")
    return dominant


def _estimate_composition(image: np.ndarray) -> str:
    grayscale = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(grayscale, 80, 160)
    thirds = np.array_split(edges, 3, axis=1)
    densities = [float(np.count_nonzero(section)) / float(section.size) for section in thirds]
    max_index = int(np.argmax(densities))
    mean_density = float(sum(densities) / len(densities))
    if mean_density == 0:
        return "balanced"
    if densities[max_index] < mean_density * 1.2:
        return "balanced"
    return ["left_focus", "center_focus", "right_focus"][max_index]


def _detect_chart_like_layout(image: np.ndarray, has_text: bool, face_count: int) -> bool:
    grayscale = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(grayscale, 80, 180)
    lines = cv2.HoughLinesP(
        edges,
        1,
        np.pi / 180,
        threshold=35,
        minLineLength=max(25, int(image.shape[1] * 0.12)),
        maxLineGap=8,
    )
    if lines is None:
        return False

    horizontal = 0
    vertical = 0
    horizontal_positions: list[int] = []
    vertical_positions: list[int] = []
    for line in lines[:, 0]:
        x1, y1, x2, y2 = [int(value) for value in line]
        dx = abs(x2 - x1)
        dy = abs(y2 - y1)
        if dx >= image.shape[1] * 0.18 and dy <= 6:
            horizontal += 1
            horizontal_positions.append(int((y1 + y2) / 2))
        if dy >= image.shape[0] * 0.18 and dx <= 6:
            vertical += 1
            vertical_positions.append(int((x1 + x2) / 2))

    unique_horizontal = _cluster_positions(horizontal_positions, tolerance=8)
    unique_vertical = _cluster_positions(vertical_positions, tolerance=8)
    if face_count > 0 and not has_text:
        return False
    if face_count > 0:
        return bool(
            horizontal >= 8
            and vertical >= 4
            and len(unique_horizontal) >= 4
            and len(unique_vertical) >= 3
        )
    if horizontal >= 4 and vertical >= 2 and len(unique_horizontal) >= 3 and len(unique_vertical) >= 2:
        return True
    return bool(horizontal >= 7 and vertical >= 3 and not has_text)


def _detect_map_like_layout(image: np.ndarray, face_count: int, has_text: bool) -> bool:
    if face_count > 0:
        return False

    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    blue_mask = cv2.inRange(hsv, (90, 40, 40), (130, 255, 255))
    green_mask = cv2.inRange(hsv, (35, 30, 30), (90, 255, 255))
    blue_ratio = float(np.count_nonzero(blue_mask)) / float(blue_mask.size)
    green_ratio = float(np.count_nonzero(green_mask)) / float(green_mask.size)
    return bool(blue_ratio >= 0.15 and green_ratio >= 0.08 and not has_text)


def _classify_visual_style(
    image: np.ndarray,
    has_text: bool,
    face_count: int,
    contains_chart: bool,
) -> str:
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    saturation = float(np.mean(hsv[:, :, 1])) / 255.0
    grayscale = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    contrast = float(np.std(grayscale))
    edges = cv2.Canny(grayscale, 80, 160)
    edge_density = float(np.count_nonzero(edges)) / float(edges.size)

    if contains_chart:
        return "chart"
    if face_count > 0 and saturation >= 0.25:
        return "photo"
    if has_text and contrast >= 45 and edge_density >= 0.08:
        return "graphic"
    if saturation >= 0.32 and edge_density >= 0.09:
        return "mixed"
    return "simple"


def _cluster_positions(values: list[int], tolerance: int) -> list[int]:
    if not values:
        return []
    ordered = sorted(values)
    clusters = [ordered[0]]
    for value in ordered[1:]:
        if abs(value - clusters[-1]) > tolerance:
            clusters.append(value)
    return clusters


def _normalize_ocr_text(chunks: list[str]) -> str | None:
    normalized_chunks: list[str] = []
    for chunk in chunks:
        compact = " ".join(chunk.split())
        if compact:
            normalized_chunks.append(compact)
    if not normalized_chunks:
        return None
    return " ".join(normalized_chunks)


def _to_confidence(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
