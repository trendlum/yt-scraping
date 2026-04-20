from __future__ import annotations

import argparse
import json
import os
from typing import Any, Sequence

from ..ai_usage import AiUsage, format_ai_usage
from ..clients.supabase import SupabaseClient
from ..config import load_dotenv
from ..exceptions import ConfigurationError
from ..repositories.supabase import SupabaseRepository
from ..services.topic_clustering import TopicClusterClient


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the topic_cluster prompt against real Supabase videos by video_id."
    )
    parser.add_argument(
        "--video-id",
        action="append",
        dest="video_ids",
        required=True,
        help="Video ID to classify. Repeat the flag for multiple IDs.",
    )
    parser.add_argument(
        "--model",
        help="Override model, for example deepseek-reasoner or gpt-4.1-mini.",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=600,
        help="Max completion/output tokens.",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output.",
    )
    return parser


def _require(value: str | None, message: str) -> str:
    if value:
        return value
    raise ConfigurationError(message)


def _repository_from_env() -> SupabaseRepository:
    supabase_url = _require(
        os.getenv("SUPABASE_URL"),
        "Missing SUPABASE_URL in environment or .env",
    )
    supabase_key = _require(
        os.getenv("SUPABASE_SERVICE_ROLE_KEY"),
        "Missing SUPABASE_SERVICE_ROLE_KEY in environment or .env",
    )
    return SupabaseRepository(
        SupabaseClient(
            supabase_url=supabase_url,
            supabase_key=supabase_key,
        )
    )


def _result_payload(video: dict[str, Any], result: Any) -> dict[str, Any]:
    return {
        "input": {
            "video_id": video["video_id"],
            "channel_handle": video["channel_handle"],
            "channel_niche": video["channel_niche"],
            "title": video["title"],
            "thumbnail_text": video["thumbnail_text"],
        },
        "existing": {
            "format_type": video["existing_format_type"],
            "promise_type": video["existing_promise_type"],
            "topic_cluster_status": video["existing_topic_cluster_status"],
        },
        "output": {
            "topic_clusters": result.topic_clusters,
            "format_type": result.format_type,
            "promise_type": result.promise_type,
            "model": result.model,
            "provider": result.provider,
        },
        "usage": result.usage.to_dict() if result.usage is not None else None,
        "usage_summary": format_ai_usage(result.usage, include_model=True),
    }


def main(argv: Sequence[str] | None = None) -> int:
    load_dotenv()
    parser = build_argument_parser()
    args = parser.parse_args(argv)

    ordered_video_ids = [str(video_id).strip() for video_id in (args.video_ids or []) if str(video_id).strip()]
    repository = _repository_from_env()
    videos = repository.get_topic_cluster_debug_inputs(ordered_video_ids)
    found_ids = {video["video_id"] for video in videos}
    missing_ids = [video_id for video_id in ordered_video_ids if video_id not in found_ids]
    if missing_ids:
        raise ConfigurationError(f"video_id no encontrado en Supabase: {', '.join(missing_ids)}")

    client = TopicClusterClient(model=args.model, max_tokens=args.max_tokens)
    total_usage = AiUsage()
    total_usage_model: str | None = None
    total_usage_provider: str | None = None
    for index, video in enumerate(videos, start=1):
        title = str(video.get("title") or "").strip()
        channel_niche = str(video.get("channel_niche") or "").strip()
        if not title or not channel_niche:
            raise ConfigurationError(
                f"El video {video['video_id']} no tiene title o channel_niche suficientes para clasificar."
            )
        result = client.classify(
            title=title,
            thumbnail_text=video.get("thumbnail_text"),
            channel_niche=channel_niche,
        )
        if result.usage is not None:
            total_usage = total_usage + result.usage
            if total_usage_model is None:
                total_usage_model = result.usage.model
            if total_usage_provider is None:
                total_usage_provider = result.usage.provider
        payload = _result_payload(video, result)
        if len(videos) > 1:
            print(f"=== VIDEO {index} | {video['video_id']} ===")
        if args.pretty or len(videos) > 1:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print(json.dumps(payload, ensure_ascii=False))
    if len(videos) > 1:
        print("=== TOTAL ===")
        total_usage = AiUsage(
            prompt_tokens=total_usage.prompt_tokens,
            completion_tokens=total_usage.completion_tokens,
            total_tokens=total_usage.total_tokens,
            cached_prompt_tokens=total_usage.cached_prompt_tokens,
            estimated_cost_usd=total_usage.estimated_cost_usd,
            calls=total_usage.calls,
            priced_calls=total_usage.priced_calls,
            model=total_usage_model,
            provider=total_usage_provider,
        )
        print(format_ai_usage(total_usage, include_model=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
