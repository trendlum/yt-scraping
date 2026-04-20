from __future__ import annotations

import os
import subprocess
import sys
import threading
import time
import shutil
from pathlib import Path

from .clients.supabase import SupabaseClient
from .config import load_dotenv
from .dashboard_api import create_server
from .repositories.dashboard import DashboardRepository


REPO_ROOT = Path(__file__).resolve().parents[2]
API_HOST = os.getenv("YT_DASHBOARD_API_HOST", "127.0.0.1")
API_PORT = int(os.getenv("YT_DASHBOARD_API_PORT", "8787"))
API_URL = f"http://{API_HOST}:{API_PORT}"


def _terminate_process(process: subprocess.Popen[str] | None) -> None:
    if process is None:
        return
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()


def _resolve_npm_executable() -> str:
    npm_executable = os.getenv("NPM_EXECUTABLE")
    if npm_executable:
        return npm_executable

    resolved = shutil.which("npm")
    if resolved:
        return resolved

    if os.name == "nt":
        resolved = shutil.which("npm.cmd")
        if resolved:
            return resolved

    raise RuntimeError("Could not find npm on PATH. Set NPM_EXECUTABLE if needed.")


def _start_api_server() -> tuple[object, threading.Thread]:
    load_dotenv()
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not supabase_url or not supabase_key:
        raise RuntimeError("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY in environment or .env")

    repository = DashboardRepository(
        SupabaseClient(
            supabase_url=supabase_url,
            supabase_key=supabase_key,
        )
    )
    server = create_server(API_HOST, API_PORT, repository)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def main() -> int:
    npm_executable = _resolve_npm_executable()
    web_process: subprocess.Popen[str] | None = None
    server = None

    try:
        server, api_thread = _start_api_server()
        deadline = time.time() + 10
        while time.time() < deadline:
            if api_thread.is_alive():
                break
            time.sleep(0.1)

        web_process = subprocess.Popen(
            [npm_executable, "--prefix", str(REPO_ROOT / "public" / "dashboard"), "run", "dev", "--", "--host", "127.0.0.1"],
            cwd=str(REPO_ROOT),
        )

        print(f"Dashboard API: {API_URL}")
        print("Dashboard UI: http://127.0.0.1:5173")
        print("Press Ctrl+C to stop both processes.")

        while True:
            if web_process.poll() is not None:
                return web_process.returncode or 0
            time.sleep(1)
    except KeyboardInterrupt:
        return 130
    finally:
        _terminate_process(web_process)
        if server is not None:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    raise SystemExit(main())
