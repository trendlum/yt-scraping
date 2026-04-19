from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from .config import load_dotenv
from .constants import DEFAULT_FEATURE_WORKERS, DEFAULT_MONITOR_DAYS, DEFAULT_TIMEOUT
from .exceptions import ConfigurationError, SupabaseAPIError
from .logging import configure_logging
from .services.transcript_backfill import backfill_recent_transcripts


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Backfill YouTube transcripts for recent videos stored in Supabase."
    )
    parser.add_argument("--supabase-url", help="Supabase project URL. Falls back to SUPABASE_URL.")
    parser.add_argument(
        "--supabase-key",
        help="Supabase service role key. Falls back to SUPABASE_SERVICE_ROLE_KEY.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Maximum number of recent videos per channel to inspect.",
    )
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
        help="Only backfill transcripts for videos published in the last N days.",
    )
    parser.add_argument(
        "--feature-workers",
        type=int,
        default=DEFAULT_FEATURE_WORKERS,
        help="Maximum worker threads used to enrich transcripts.",
    )
    parser.add_argument(
        "--output",
        help="Optional output JSON path. Defaults to stdout.",
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

    supabase_url = _require(
        args.supabase_url or os.getenv("SUPABASE_URL"),
        "Missing Supabase URL. Provide --supabase-url or set SUPABASE_URL in .env",
    )
    supabase_key = _require(
        args.supabase_key or os.getenv("SUPABASE_SERVICE_ROLE_KEY"),
        "Missing Supabase key. Provide --supabase-key or set SUPABASE_SERVICE_ROLE_KEY in .env",
    )

    try:
        result: list[dict[str, Any]] = backfill_recent_transcripts(
            supabase_url=supabase_url,
            supabase_key=supabase_key,
            limit=args.limit,
            timeout=args.timeout,
            monitor_days=args.monitor_days,
            feature_workers=args.feature_workers,
        )
    except (ConfigurationError, SupabaseAPIError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc

    output = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(output, encoding="utf-8")
    else:
        print(output)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
