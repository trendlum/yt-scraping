from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

import requests

from ..analytics.thumbnail_features import ThumbnailFeatureExtractor


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Test thumbnail extraction from a local image path or a thumbnail URL."
    )
    parser.add_argument(
        "input",
        help="Local image path or image URL.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="HTTP timeout in seconds when input is a URL.",
    )
    parser.add_argument(
        "--disable-ocr",
        action="store_true",
        help="Skip OCR and only run non-OCR thumbnail analysis.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print the full thumbnail feature payload.",
    )
    return parser


def load_image_from_input(value: str, timeout: int) -> tuple[bytes, str]:
    candidate = Path(value)
    if candidate.exists() and candidate.is_file():
        return candidate.read_bytes(), str(candidate)

    response = requests.get(value, timeout=timeout)
    response.raise_for_status()
    return response.content, value


def format_result(features, *, verbose: bool) -> str:
    if not verbose:
        lines = [
            f"has_thumbnail_text: {features.has_thumbnail_text}",
            f"thumbnail_text: {features.thumbnail_text}",
            f"thumbnail_text_confidence: {features.thumbnail_text_confidence}",
        ]
        return "\n".join(lines)

    lines = [
        f"status: {features.status}",
        f"ocr_status: {features.ocr_status}",
        f"has_face: {features.has_face}",
        f"face_count: {features.face_count}",
        f"has_thumbnail_text: {features.has_thumbnail_text}",
        f"estimated_thumbnail_text_tokens: {features.estimated_thumbnail_text_tokens}",
        f"thumbnail_text: {features.thumbnail_text}",
        f"thumbnail_text_confidence: {features.thumbnail_text_confidence}",
        f"dominant_colors: {features.dominant_colors}",
        f"composition_type: {features.composition_type}",
        f"contains_chart: {features.contains_chart}",
        f"contains_map: {features.contains_map}",
        f"visual_style: {features.visual_style}",
    ]
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_argument_parser()
    args = parser.parse_args(argv)

    image_bytes, source = load_image_from_input(args.input, args.timeout)
    extractor = ThumbnailFeatureExtractor(enable_ocr=not args.disable_ocr)
    features = extractor.extract_from_bytes(image_bytes)

    print(f"source: {source}")
    print(format_result(features, verbose=args.verbose))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
