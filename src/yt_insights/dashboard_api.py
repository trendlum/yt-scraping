from __future__ import annotations

import json
import os
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse

from .clients.supabase import SupabaseClient
from .config import load_dotenv
from .exceptions import ConfigurationError, SupabaseAPIError
from .repositories.dashboard import DashboardFilters, DashboardRepository


def _json_bytes(payload: Any) -> bytes:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def _require(value: str | None, message: str) -> str:
    if value:
        return value
    raise ConfigurationError(message)


def _parse_filters(query: dict[str, list[str]]) -> DashboardFilters:
    def first(name: str) -> str | None:
        values = query.get(name)
        if not values:
            return None
        value = values[0].strip()
        return value or None

    window_value = first("analysis_window")
    threshold_value = first("min_sample_threshold")
    return DashboardFilters(
        analysis_window=int(window_value) if window_value else None,
        analysis_date=first("analysis_date"),
        niche=first("niche"),
        channel_handle=first("channel_handle"),
        topic_cluster=first("topic_cluster"),
        niche_growth_status=first("niche_growth_status"),
        channel_growth_status=first("channel_growth_status"),
        topic_type=first("topic_type"),
        performance_label=first("performance_label"),
        video_type=first("video_type"),
        sample_confidence=first("sample_confidence"),
        min_sample_threshold=int(threshold_value) if threshold_value else None,
    )


class DashboardRequestHandler(BaseHTTPRequestHandler):
    repository: DashboardRepository | None = None

    def _send_json(self, status_code: int, payload: Any) -> None:
        body = _json_bytes(payload)
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        assert self.repository is not None

        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        filters = _parse_filters(query)

        try:
            if parsed.path == "/api/health":
                self._send_json(200, {"status": "ok"})
                return

            if parsed.path == "/api/dashboard/meta":
                self._send_json(200, self.repository.get_meta())
                return

            if parsed.path == "/api/dashboard/overview":
                self._send_json(200, self.repository.get_overview(filters))
                return

            if parsed.path == "/api/dashboard/niches":
                self._send_json(200, {"items": self.repository.list_niches(filters)})
                return

            if parsed.path == "/api/dashboard/niche-detail":
                niche = query.get("niche", [""])[0]
                detail = self.repository.get_niche_detail(filters, niche)
                self._send_json(200, detail or {"row": None})
                return

            if parsed.path == "/api/dashboard/channels":
                self._send_json(200, {"items": self.repository.list_channels(filters)})
                return

            if parsed.path == "/api/dashboard/channel-detail":
                channel_handle = query.get("channel_handle", [""])[0]
                detail = self.repository.get_channel_detail(filters, channel_handle)
                self._send_json(200, detail or {"row": None})
                return

            if parsed.path == "/api/dashboard/topics":
                self._send_json(200, {"items": self.repository.list_topics(filters)})
                return

            if parsed.path == "/api/dashboard/topic-detail":
                topic_cluster = query.get("topic_cluster", [""])[0]
                detail = self.repository.get_topic_detail(filters, topic_cluster)
                self._send_json(200, detail or {"row": None})
                return

            if parsed.path == "/api/dashboard/videos":
                video_type = query.get("video_type", ["underpackaged"])[0]
                filters = DashboardFilters(**{**asdict(filters), "video_type": video_type})
                self._send_json(200, {"items": self.repository.list_videos(filters, video_type=video_type)})
                return

            if parsed.path == "/api/dashboard/video-detail":
                video_id = query.get("video_id", [""])[0]
                detail = self.repository.get_video_detail(filters, video_id)
                self._send_json(200, detail or {"row": None})
                return

            self._send_json(404, {"error": "Not found"})
        except SupabaseAPIError as exc:
            self._send_json(502, {"error": str(exc)})
        except Exception as exc:  # noqa: BLE001
            self._send_json(500, {"error": str(exc)})


def main() -> int:
    load_dotenv()
    supabase_url = _require(os.getenv("SUPABASE_URL"), "Missing SUPABASE_URL in environment or .env")
    supabase_key = _require(
        os.getenv("SUPABASE_SERVICE_ROLE_KEY"),
        "Missing SUPABASE_SERVICE_ROLE_KEY in environment or .env",
    )
    host = os.getenv("YT_DASHBOARD_API_HOST", "127.0.0.1")
    port = int(os.getenv("YT_DASHBOARD_API_PORT", "8787"))

    repository = DashboardRepository(
        SupabaseClient(
            supabase_url=supabase_url,
            supabase_key=supabase_key,
        )
    )
    server = create_server(host, port, repository)
    print(f"Dashboard API listening on http://{host}:{port}")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

    return 0


def create_server(
    host: str,
    port: int,
    repository: DashboardRepository,
) -> ThreadingHTTPServer:
    DashboardRequestHandler.repository = repository
    return ThreadingHTTPServer((host, port), DashboardRequestHandler)
