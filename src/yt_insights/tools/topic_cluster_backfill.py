from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Sequence

from ..clients.supabase import SupabaseClient
from ..config import load_dotenv
from ..constants import DEFAULT_TOPIC_CLUSTER_PAGE_SIZE, DEFAULT_TOPIC_CLUSTER_WORKERS
from ..exceptions import ConfigurationError
from ..logging import configure_logging
from ..repositories.supabase import SupabaseRepository
from ..services.topic_clustering import run_topic_cluster_backfill


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Backfill topic clusters, format_type and promise_type for all Supabase videos."
    )
    parser.add_argument(
        "--supabase-url",
        help="Supabase project URL. Falls back to SUPABASE_URL.",
    )
    parser.add_argument(
        "--supabase-key",
        help="Supabase service role key. Falls back to SUPABASE_SERVICE_ROLE_KEY.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=DEFAULT_TOPIC_CLUSTER_WORKERS,
        help="Maximum worker threads used for LLM calls.",
    )
    parser.add_argument(
        "--page-size",
        type=int,
        default=DEFAULT_TOPIC_CLUSTER_PAGE_SIZE,
        help="Batch size used when scanning Supabase videos.",
    )
    parser.add_argument(
        "--model",
        help="Override model, for example deepseek-chat or deepseek-reasoner.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        help="Python logging level. Example: INFO, DEBUG, WARNING.",
    )
    parser.add_argument(
        "--output",
        help="Optional output JSON path. Defaults to stdout.",
    )
    return parser


def _require(value: str | None, message: str) -> str:
    if value:
        return value
    raise ConfigurationError(message)


def main(argv: Sequence[str] | None = None) -> int:
    load_dotenv()
    parser = build_argument_parser()
    args = parser.parse_args(argv)

    configure_logging(args.log_level)

    supabase_url = args.supabase_url or os.getenv("SUPABASE_URL")
    supabase_key = args.supabase_key or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    repository = SupabaseRepository(
        SupabaseClient(
            supabase_url=_require(supabase_url, "Missing Supabase URL. Provide --supabase-url or set SUPABASE_URL in .env"),
            supabase_key=_require(
                supabase_key,
                "Missing Supabase key. Provide --supabase-key or set SUPABASE_SERVICE_ROLE_KEY in .env",
            ),
        )
    )

    from ..services.topic_clustering import TopicClusterClient

    client = TopicClusterClient(model=args.model)
    stats = run_topic_cluster_backfill(
        repository,
        client=client,
        workers=args.workers,
        page_size=args.page_size,
    )
    result = {
        "scanned": stats.scanned,
        "processed": stats.processed,
        "skipped": stats.skipped,
        "failed": stats.failed,
        "usage": stats.usage.to_dict() if stats.usage is not None else None,
    }
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
