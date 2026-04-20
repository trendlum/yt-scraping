from __future__ import annotations

from dataclasses import dataclass
import os
import re
from threading import Lock, local
from typing import Any


_DEFAULT_PRICING: dict[tuple[str, str], dict[str, float]] = {
    ("deepseek", "DEEPSEEK_REASONER"): {
        "input": 0.55,
        "cached_input": 0.14,
        "output": 2.19,
    },
    ("deepseek", "DEEPSEEK_CHAT"): {
        "input": 0.27,
        "cached_input": 0.07,
        "output": 1.10,
    },
    ("openai", "GPT_4_1_MINI"): {
        "input": 0.40,
        "cached_input": 0.10,
        "output": 1.60,
    },
    ("openai", "GPT_5_4_MINI"): {
        "input": 0.75,
        "cached_input": 0.075,
        "output": 4.50,
    },
}


@dataclass(frozen=True)
class AiUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cached_prompt_tokens: int = 0
    estimated_cost_usd: float | None = None
    calls: int = 0
    priced_calls: int = 0
    model: str | None = None
    provider: str | None = None

    def __add__(self, other: "AiUsage") -> "AiUsage":
        combined_cost: float | None = None
        if self.estimated_cost_usd is not None or other.estimated_cost_usd is not None:
            combined_cost = (self.estimated_cost_usd or 0.0) + (other.estimated_cost_usd or 0.0)
        return AiUsage(
            prompt_tokens=self.prompt_tokens + other.prompt_tokens,
            completion_tokens=self.completion_tokens + other.completion_tokens,
            total_tokens=self.total_tokens + other.total_tokens,
            cached_prompt_tokens=self.cached_prompt_tokens + other.cached_prompt_tokens,
            estimated_cost_usd=combined_cost,
            calls=self.calls + other.calls,
            priced_calls=self.priced_calls + other.priced_calls,
        )

    def __sub__(self, other: "AiUsage") -> "AiUsage":
        estimated_cost_usd: float | None = None
        if self.estimated_cost_usd is not None or other.estimated_cost_usd is not None:
            estimated_cost_usd = (self.estimated_cost_usd or 0.0) - (other.estimated_cost_usd or 0.0)
        return AiUsage(
            prompt_tokens=self.prompt_tokens - other.prompt_tokens,
            completion_tokens=self.completion_tokens - other.completion_tokens,
            total_tokens=self.total_tokens - other.total_tokens,
            cached_prompt_tokens=self.cached_prompt_tokens - other.cached_prompt_tokens,
            estimated_cost_usd=estimated_cost_usd,
            calls=self.calls - other.calls,
            priced_calls=self.priced_calls - other.priced_calls,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "model": self.model,
            "provider": self.provider,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "cached_prompt_tokens": self.cached_prompt_tokens,
            "estimated_cost_usd": self.estimated_cost_usd,
            "calls": self.calls,
            "priced_calls": self.priced_calls,
        }


_USAGE_LOCK = Lock()
_USAGE_TOTALS = AiUsage()
_THREAD_USAGE_STATE = local()


def _normalized_model_key(model: str) -> str:
    return re.sub(r"[^A-Z0-9]+", "_", model.upper()).strip("_")


def _float_from_env(*names: str) -> float | None:
    for name in names:
        raw_value = os.getenv(name, "").strip()
        if raw_value:
            return float(raw_value)
    return None


def _extract_cached_prompt_tokens(usage_payload: dict[str, Any]) -> int:
    for details_key in ("prompt_tokens_details", "input_tokens_details"):
        details = usage_payload.get(details_key)
        if isinstance(details, dict):
            value = details.get("cached_tokens")
            if value is not None:
                return int(value)
    cached_value = usage_payload.get("prompt_cache_hit_tokens")
    if cached_value is not None:
        return int(cached_value)
    return 0


def estimate_cost_usd(*, model: str | None, provider: str | None, usage: dict[str, Any]) -> float | None:
    if not model:
        return None

    normalized_model = _normalized_model_key(model)
    normalized_provider = provider.upper() if provider else None
    env_prefixes = [f"AI_PRICE_{normalized_model}"]
    if normalized_provider:
        env_prefixes.insert(0, f"{normalized_provider}_PRICE_{normalized_model}")

    input_price: float | None = None
    output_price: float | None = None
    cached_input_price: float | None = None
    for prefix in env_prefixes:
        input_price = _float_from_env(f"{prefix}_INPUT_PER_MILLION_USD", f"{prefix}_INPUT_PER_MILLION")
        output_price = _float_from_env(f"{prefix}_OUTPUT_PER_MILLION_USD", f"{prefix}_OUTPUT_PER_MILLION")
        cached_input_price = _float_from_env(
            f"{prefix}_CACHED_INPUT_PER_MILLION_USD",
            f"{prefix}_CACHED_INPUT_PER_MILLION",
        )
        if input_price is not None or output_price is not None or cached_input_price is not None:
            break

    if input_price is None and output_price is None and cached_input_price is None and provider:
        defaults = _DEFAULT_PRICING.get((provider.lower(), normalized_model))
        if defaults:
            input_price = defaults["input"]
            output_price = defaults["output"]
            cached_input_price = defaults["cached_input"]

    if input_price is None and output_price is None and cached_input_price is None:
        return None

    prompt_tokens = int(usage.get("prompt_tokens", usage.get("input_tokens", 0)) or 0)
    completion_tokens = int(usage.get("completion_tokens", usage.get("output_tokens", 0)) or 0)
    cached_prompt_tokens = _extract_cached_prompt_tokens(usage)
    uncached_prompt_tokens = max(prompt_tokens - cached_prompt_tokens, 0)
    resolved_input_price = input_price or 0.0
    resolved_output_price = output_price or 0.0
    resolved_cached_price = cached_input_price if cached_input_price is not None else resolved_input_price

    return (
        (uncached_prompt_tokens * resolved_input_price)
        + (cached_prompt_tokens * resolved_cached_price)
        + (completion_tokens * resolved_output_price)
    ) / 1_000_000


def extract_ai_usage(response: Any, *, provider: str | None = None, model: str | None = None) -> AiUsage | None:
    usage = getattr(response, "usage", None)
    if usage is None:
        return None

    if hasattr(usage, "model_dump"):
        usage_payload = usage.model_dump()
    elif hasattr(usage, "to_dict"):
        usage_payload = usage.to_dict()
    elif isinstance(usage, dict):
        usage_payload = dict(usage)
    else:
        usage_payload = {}

    prompt_tokens = int(usage_payload.get("prompt_tokens", usage_payload.get("input_tokens", 0)) or 0)
    completion_tokens = int(usage_payload.get("completion_tokens", usage_payload.get("output_tokens", 0)) or 0)
    total_tokens = int(usage_payload.get("total_tokens", prompt_tokens + completion_tokens) or 0)
    resolved_model = model or getattr(response, "model", None)
    estimated_cost_usd = estimate_cost_usd(model=resolved_model, provider=provider, usage=usage_payload)
    return AiUsage(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        cached_prompt_tokens=_extract_cached_prompt_tokens(usage_payload),
        estimated_cost_usd=estimated_cost_usd,
        calls=1,
        priced_calls=1 if estimated_cost_usd is not None else 0,
        model=resolved_model,
        provider=provider,
    )


def record_ai_usage(usage: AiUsage | None) -> AiUsage | None:
    global _USAGE_TOTALS
    if usage is None:
        return None
    with _USAGE_LOCK:
        _USAGE_TOTALS = _USAGE_TOTALS + usage
    current_thread_usage = getattr(_THREAD_USAGE_STATE, "totals", AiUsage())
    _THREAD_USAGE_STATE.totals = current_thread_usage + usage
    return usage


def get_ai_usage_snapshot() -> AiUsage:
    with _USAGE_LOCK:
        return _USAGE_TOTALS


def format_ai_usage(usage: AiUsage | None, *, include_model: bool = False) -> str:
    if usage is None or usage.calls <= 0 or usage.total_tokens <= 0:
        return "sin uso de tokens"

    parts = [f"tokens in/out/total: {usage.prompt_tokens}/{usage.completion_tokens}/{usage.total_tokens}"]
    if usage.cached_prompt_tokens > 0:
        parts.append(f"cached: {usage.cached_prompt_tokens}")
    if usage.priced_calls > 0 and usage.estimated_cost_usd is not None:
        parts.append(f"coste aprox: ${usage.estimated_cost_usd:.6f}")
    else:
        parts.append("coste aprox: n/d")
    if include_model and usage.model:
        parts.append(f"modelo: {usage.model}")
    return " | ".join(parts)
