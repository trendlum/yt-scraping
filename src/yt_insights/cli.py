from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from .config import load_dotenv
from .constants import (
    DEFAULT_BASELINE_WINDOW_DAYS,
    DEFAULT_FEATURE_WORKERS,
    DEFAULT_MONITOR_DAYS,
    DEFAULT_TIMEOUT,
)
from .exceptions import ConfigurationError, SupabaseAPIError, YouTubeAPIError
from .logging import configure_logging
from .services.scraper import scrape_and_store_channels, scrape_channel_latest_videos


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Fetch YouTube videos, store current state and build basic performance analytics."
    )
    parser.add_argument("--api-key", help="YouTube Data API v3 key. Falls back to YT_API_KEY.")
    parser.add_argument("--channel-handle", help="Optional single YouTube channel handle.")
    parser.add_argument(
        "--limit",
        type=int,
        help="Maximum number of latest uploads to fetch per channel.",
    )
    parser.add_argument("--supabase-url", help="Supabase project URL. Falls back to SUPABASE_URL.")
    parser.add_argument(
        "--supabase-key",
        help="Supabase service role key. Falls back to SUPABASE_SERVICE_ROLE_KEY.",
    )
    parser.add_argument("--output", help="Optional output JSON path. Defaults to stdout.")
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT,
        help="HTTP timeout in seconds.",
    )
    parser.add_argument(
        "--monitor-days",
        type=int,
        default=DEFAULT_MONITOR_DAYS,
        help="In batch mode, refresh videos published in the last N days.",
    )
    parser.add_argument(
        "--baseline-window-days",
        type=int,
        default=DEFAULT_BASELINE_WINDOW_DAYS,
        help="Publication window used to build per-channel baselines.",
    )
    parser.add_argument(
        "--feature-workers",
        type=int,
        default=DEFAULT_FEATURE_WORKERS,
        help="Maximum worker threads used to enrich transcripts and thumbnails.",
    )
    parser.add_argument(
        "--skip-transcripts",
        action="store_true",
        default=os.getenv("GITHUB_ACTIONS", "").lower() == "true",
        help="Disable transcript enrichment in batch mode.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        help="Python logging level. Example: INFO, DEBUG, WARNING.",
    )
    return parser


def _require(value: str | None, message: str) -> str:
    if value:
        return value
    raise ConfigurationError(message)


def main() -> int:
    load_dotenv()
    parser = build_argument_parser()
    args = parser.parse_args()

    configure_logging(args.log_level)

    api_key = _require(
        args.api_key or os.getenv("YT_API_KEY"),
        "Missing API key. Provide --api-key or set YT_API_KEY in .env",
    )

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
            result = scrape_and_store_channels(
                api_key=api_key,
                supabase_url=_require(
                    supabase_url,
                    "Missing Supabase URL. Provide --supabase-url or set SUPABASE_URL in .env",
                ),
                supabase_key=_require(
                    supabase_key,
                    "Missing Supabase key. Provide --supabase-key or set SUPABASE_SERVICE_ROLE_KEY in .env",
                ),
                limit=args.limit,
                timeout=args.timeout,
                monitor_days=args.monitor_days,
                baseline_window_days=args.baseline_window_days,
                feature_workers=args.feature_workers,
                should_analyze_transcript=not args.skip_transcripts,
            )
    except (ConfigurationError, YouTubeAPIError, SupabaseAPIError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc

    output = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(output, encoding="utf-8")
    else:
        print(output)

    return 0
