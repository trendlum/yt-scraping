from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime
import json
import logging
import os
import re
from pathlib import Path
from typing import Any

from openai import OpenAI
import yaml

from ..ai_usage import AiUsage, extract_ai_usage, format_ai_usage, get_ai_usage_snapshot, record_ai_usage
from ..constants import DEFAULT_TOPIC_CLUSTER_PAGE_SIZE, DEFAULT_TOPIC_CLUSTER_WORKERS
from ..models import serialize_datetime, sha1_text, utc_now


LOGGER = logging.getLogger(__name__)
BOT_PROMPT_PATH = Path(__file__).resolve().parents[3] / "bots" / "topic_cluster.txt"
ALLOWED_FORMAT_TYPES = {
    "data_analysis",
    "news_breakdown",
    "explainer",
    "opinion_take",
    "prediction_forecast",
    "comparison",
    "case_study",
    "interview",
    "reaction",
    "listicle",
}
ALLOWED_PROMISE_TYPES = {
    "revelation",
    "warning",
    "how_to",
    "explanation",
    "prediction",
    "comparison",
    "opinion",
    "news",
    "deep_dive",
}


@dataclass(frozen=True)
class TopicClusterPrompt:
    description: str
    model: str
    system_prompt: str
    user_template: str
    prompt_fingerprint: str


@dataclass(frozen=True)
class TopicClusterResult:
    topic_clusters: list[str]
    format_type: str
    promise_type: str
    usage: AiUsage | None
    model: str
    provider: str


@dataclass(frozen=True)
class TopicClusterRunStats:
    scanned: int = 0
    processed: int = 0
    skipped: int = 0
    failed: int = 0
    usage: AiUsage | None = None


def _supports_temperature(model: str) -> bool:
    normalized = model.lower()
    return not normalized.startswith("deepseek-reasoner") and not normalized.startswith("o")


def _extract_text_from_response(response: Any) -> str:
    for attr_name in ("output_text", "text"):
        candidate = getattr(response, attr_name, None)
        if isinstance(candidate, str) and candidate.strip():
            return candidate

    choices = getattr(response, "choices", None)
    if isinstance(choices, list) and choices:
        message = getattr(choices[0], "message", None)
        if message is not None:
            for attr_name in ("content", "reasoning_content"):
                candidate = getattr(message, attr_name, None)
                if isinstance(candidate, str) and candidate.strip():
                    return candidate
            if isinstance(message, dict):
                for attr_name in ("content", "reasoning_content"):
                    candidate = message.get(attr_name)
                    if isinstance(candidate, str) and candidate.strip():
                        return candidate
    if isinstance(response, dict):
        for attr_name in ("output_text", "text"):
            candidate = response.get(attr_name)
            if isinstance(candidate, str) and candidate.strip():
                return candidate
    return ""


def _extract_json_from_text(text: str) -> dict[str, Any]:
    if not text.strip():
        raise RuntimeError("DeepSeek devolvio contenido vacio.")

    candidate = text.strip()
    if candidate.startswith("```"):
        match = re.search(r"```(?:json)?\s*(.*?)\s*```", candidate, re.DOTALL | re.IGNORECASE)
        if match:
            candidate = match.group(1).strip()

    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError as exc:
        match = re.search(r"\{.*\}", candidate, re.DOTALL)
        if not match:
            raise RuntimeError(f"Respuesta no JSON. Preview: {candidate[:300]!r}") from exc
        parsed = json.loads(match.group(0))

    if not isinstance(parsed, dict):
        raise RuntimeError("La respuesta JSON debe ser un objeto.")
    return parsed


def load_topic_cluster_prompt(prompt_path: Path = BOT_PROMPT_PATH) -> TopicClusterPrompt:
    raw_text = prompt_path.read_text(encoding="utf-8")
    payload = yaml.safe_load(raw_text)
    prompt_payload = payload["prompt"]
    system_prompt = str(prompt_payload["system"]).strip()
    examples = prompt_payload.get("examples") or []
    if examples:
        rendered_examples: list[str] = []
        for example in examples:
            rendered_examples.append(
                "\n".join(
                    [
                        f"Title: {example['title']}",
                        f"Thumbnail text: {example['thumbnail_text']}",
                        f"Channel niche: {example['channel_niche']}",
                        f"JSON: {str(example['output']).strip()}",
                    ]
                )
            )
        system_prompt = system_prompt + "\n\n--- EXAMPLES ---\n\n" + "\n\n".join(rendered_examples)
    return TopicClusterPrompt(
        description=str(prompt_payload.get("description", "topic clustering")).strip(),
        model=str(prompt_payload.get("model", "deepseek-reasoner")).strip() or "deepseek-reasoner",
        system_prompt=system_prompt,
        user_template=str(prompt_payload["user_message"]).strip(),
        prompt_fingerprint=sha1_text(raw_text),
    )


def _resolve_provider(model: str) -> str:
    if model.lower().startswith("gpt-"):
        return "openai"
    return "deepseek"


def _build_client(model: str) -> tuple[OpenAI, str]:
    provider = _resolve_provider(model)
    if provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError("Falta OPENAI_API_KEY para topic clustering.")
        base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").strip()
    else:
        api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError("Falta DEEPSEEK_API_KEY para topic clustering.")
        base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").strip()
    return OpenAI(api_key=api_key, base_url=base_url), provider


def topic_clustering_is_configured(model: str) -> bool:
    provider = _resolve_provider(model)
    if provider == "openai":
        return bool(os.getenv("OPENAI_API_KEY", "").strip())
    return bool(os.getenv("DEEPSEEK_API_KEY", "").strip())


class TopicClusterClient:
    def __init__(
        self,
        *,
        prompt: TopicClusterPrompt | None = None,
        model: str | None = None,
        fallback_model: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 600,
    ) -> None:
        self.prompt = prompt or load_topic_cluster_prompt()
        self.model = model or os.getenv("TOPIC_CLUSTER_MODEL", "").strip() or self.prompt.model
        self.fallback_model = (
            fallback_model
            or os.getenv("TOPIC_CLUSTER_FALLBACK_MODEL", "").strip()
            or ("deepseek-chat" if self.provider_is_deepseek_reasoner(self.model) else None)
        )
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._client, self.provider = _build_client(self.model)

    @staticmethod
    def provider_is_deepseek_reasoner(model: str) -> bool:
        return model.lower() == "deepseek-reasoner"

    def _request_kwargs(self, *, model: str, title: str, thumbnail_text: str | None, channel_niche: str) -> dict[str, Any]:
        user_prompt = self.prompt.user_template
        user_prompt = user_prompt.replace("{{channel_niche}}", channel_niche or "")
        user_prompt = user_prompt.replace("{{title}}", title or "")
        user_prompt = user_prompt.replace("{{thumbnail_text}}", thumbnail_text or "")
        request_kwargs: dict[str, Any] = {
            "model": model,
            "messages": [
                {"role": "system", "content": self.prompt.system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        if _resolve_provider(model) == "openai":
            request_kwargs["response_format"] = {"type": "json_object"}
        if _resolve_provider(model) == "openai" and model.lower().startswith("gpt-5"):
            request_kwargs["max_completion_tokens"] = self.max_tokens
        else:
            request_kwargs["max_tokens"] = self.max_tokens
        if _supports_temperature(model):
            request_kwargs["temperature"] = self.temperature
        return request_kwargs

    def _classify_once(
        self,
        *,
        model: str,
        title: str,
        thumbnail_text: str | None,
        channel_niche: str,
    ) -> TopicClusterResult:
        provider = _resolve_provider(model)
        client, _ = _build_client(model)
        request_kwargs = self._request_kwargs(
            model=model,
            title=title,
            thumbnail_text=thumbnail_text,
            channel_niche=channel_niche,
        )
        response = client.chat.completions.create(**request_kwargs)
        usage = record_ai_usage(extract_ai_usage(response, provider=provider, model=model))
        content = _extract_text_from_response(response)
        parsed_payload = _extract_json_from_text(content)
        topic_clusters = _normalize_topic_clusters(parsed_payload.get("topic_clusters"))
        format_type = str(parsed_payload.get("format_type", "")).strip().lower()
        promise_type = str(parsed_payload.get("promise_type", "")).strip().lower()
        if format_type not in ALLOWED_FORMAT_TYPES:
            raise RuntimeError(f"format_type invalido: {format_type!r}")
        if promise_type not in ALLOWED_PROMISE_TYPES:
            raise RuntimeError(f"promise_type invalido: {promise_type!r}")
        if not topic_clusters:
            raise RuntimeError("topic_clusters vacio")
        return TopicClusterResult(
            topic_clusters=topic_clusters,
            format_type=format_type,
            promise_type=promise_type,
            usage=usage,
            model=str(getattr(response, "model", model)),
            provider=provider,
        )

    def classify(self, *, title: str, thumbnail_text: str | None, channel_niche: str) -> TopicClusterResult:
        models_to_try = [self.model]
        if self.fallback_model and self.fallback_model not in models_to_try:
            models_to_try.append(self.fallback_model)

        last_error: Exception | None = None
        for model in models_to_try:
            try:
                return self._classify_once(
                    model=model,
                    title=title,
                    thumbnail_text=thumbnail_text,
                    channel_niche=channel_niche,
                )
            except Exception as exc:
                last_error = exc
                if model != models_to_try[-1]:
                    LOGGER.debug(
                        "Topic clustering failed for model %s; retrying fallback if available. Error: %s",
                        model,
                        exc,
                    )
        if last_error is not None:
            raise last_error
        raise RuntimeError("Topic clustering failed without a recoverable error.")


def _normalize_topic_clusters(value: Any) -> list[str]:
    if not isinstance(value, list):
        raise RuntimeError("topic_clusters debe ser una lista")
    normalized: list[str] = []
    seen: set[str] = set()
    for item in value:
        text = " ".join(str(item).strip().lower().split())
        if not text or text in seen:
            continue
        seen.add(text)
        normalized.append(text)
    return normalized[:3]


def _topic_cluster_input_fingerprint(
    *,
    prompt_fingerprint: str,
    title: str | None,
    thumbnail_text: str | None,
    channel_niche: str | None,
) -> str:
    return sha1_text(
        "\n".join(
            [
                prompt_fingerprint,
                title or "",
                thumbnail_text or "",
                channel_niche or "",
            ]
        )
    )


def _needs_topic_clustering(candidate: dict[str, Any]) -> bool:
    feature_row = candidate["feature_row"]
    if feature_row.get("topic_cluster_status") == "complete":
        has_topic_clusters = bool(feature_row.get("topic_clusters"))
        has_format_type = bool(feature_row.get("format_type"))
        has_promise_type = bool(feature_row.get("promise_type"))
        if has_topic_clusters and has_format_type and has_promise_type:
            return False
    return True


def run_topic_cluster_backfill(
    repository: Any,
    *,
    client: TopicClusterClient | None = None,
    executed_at: datetime | None = None,
    workers: int = DEFAULT_TOPIC_CLUSTER_WORKERS,
    page_size: int = DEFAULT_TOPIC_CLUSTER_PAGE_SIZE,
) -> TopicClusterRunStats:
    prompt = client.prompt if client is not None else load_topic_cluster_prompt()
    resolved_model = client.model if client is not None else os.getenv("TOPIC_CLUSTER_MODEL", "").strip() or prompt.model
    if client is None:
        if not topic_clustering_is_configured(resolved_model):
            LOGGER.info("Skipping topic clustering because no provider key is configured for model %s", resolved_model)
            return TopicClusterRunStats()
        client = TopicClusterClient(prompt=prompt, model=resolved_model)

    run_started_at = executed_at or utc_now()
    usage_before_run = get_ai_usage_snapshot()
    scanned = 0
    processed = 0
    skipped = 0
    failed = 0
    offset = 0

    while True:
        candidates = repository.list_topic_cluster_candidates(limit=page_size, offset=offset)
        if not candidates:
            break
        scanned += len(candidates)
        offset += len(candidates)

        processable = [candidate for candidate in candidates if _needs_topic_clustering(candidate)]
        skipped += len(candidates) - len(processable)
        if not processable:
            continue

        feature_rows_to_upsert: list[dict[str, Any]] = []
        topic_map: dict[str, list[str]] = {}

        def classify_candidate(candidate: dict[str, Any]) -> tuple[dict[str, Any], list[str] | None, bool]:
            feature_row = dict(candidate["feature_row"])
            fingerprint = _topic_cluster_input_fingerprint(
                prompt_fingerprint=prompt.prompt_fingerprint,
                title=candidate.get("title"),
                thumbnail_text=feature_row.get("thumbnail_text"),
                channel_niche=candidate.get("channel_niche"),
            )
            feature_row["topic_cluster_input_fingerprint"] = fingerprint
            feature_row["topic_cluster_model"] = client.model
            feature_row["topic_cluster_extracted_at"] = serialize_datetime(run_started_at)
            feature_row["updated_at"] = serialize_datetime(run_started_at)

            title = str(candidate.get("title") or "").strip()
            channel_niche = str(candidate.get("channel_niche") or "").strip()
            if not title or not channel_niche:
                feature_row["topic_cluster_status"] = "skipped"
                feature_row["topic_cluster_error"] = "missing_title_or_channel_niche"
                return feature_row, None, False

            try:
                result = client.classify(
                    title=title,
                    thumbnail_text=feature_row.get("thumbnail_text"),
                    channel_niche=channel_niche,
                )
            except Exception as exc:
                feature_row["topic_cluster_status"] = "failed"
                feature_row["topic_cluster_error"] = str(exc)[:500]
                return feature_row, None, True

            feature_row["format_type"] = result.format_type
            feature_row["promise_type"] = result.promise_type
            feature_row["topic_clusters"] = result.topic_clusters
            feature_row["topic_cluster_status"] = "complete"
            feature_row["topic_cluster_model"] = result.model
            feature_row["topic_cluster_error"] = None
            return feature_row, result.topic_clusters, False

        max_workers = max(1, min(workers, len(processable)))
        if max_workers == 1:
            results = [classify_candidate(candidate) for candidate in processable]
        else:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                results = list(executor.map(classify_candidate, processable))

        for candidate, result_tuple in zip(processable, results, strict=True):
            feature_row, topic_clusters, had_error = result_tuple
            feature_rows_to_upsert.append(feature_row)
            if topic_clusters is not None:
                topic_map[str(candidate["video_id"])] = topic_clusters
                processed += 1
            elif had_error:
                failed += 1
            else:
                skipped += 1

        repository.upsert_feature_rows(feature_rows_to_upsert)
        repository.replace_video_topics(topic_map)

    usage_delta = get_ai_usage_snapshot() - usage_before_run
    if usage_delta.calls > 0:
        LOGGER.info("Topic clustering finished | %s", format_ai_usage(usage_delta, include_model=True))
    return TopicClusterRunStats(
        scanned=scanned,
        processed=processed,
        skipped=skipped,
        failed=failed,
        usage=usage_delta,
    )
