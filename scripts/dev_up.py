#!/usr/bin/env python3
"""Start iSpan API + realtime + Ionic detached from the parent shell."""

from __future__ import annotations

import os
import signal
import subprocess
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOGS = ROOT / ".logs"
API_PORT = os.environ.get("API_PORT", "8001")
WEB_PORT = os.environ.get("WEB_PORT", "8100")
RT_PORT = os.environ.get("REALTIME_PORT", "4000")


def kill_pidfile(name: str) -> None:
    path = LOGS / name
    if not path.exists():
        return
    try:
        os.kill(int(path.read_text().strip()), signal.SIGTERM)
    except (ProcessLookupError, ValueError, PermissionError):
        pass


def spawn(cmd: list[str], cwd: Path, log_name: str, pid_name: str, env: dict | None = None) -> int:
    logf = open(LOGS / log_name, "ab", buffering=0)
    merged = {**os.environ, **(env or {})}
    proc = subprocess.Popen(
        cmd,
        cwd=str(cwd),
        stdout=logf,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        start_new_session=True,
        env=merged,
    )
    (LOGS / pid_name).write_text(str(proc.pid))
    return proc.pid


def wait_url(url: str, attempts: int = 60) -> bool:
    for _ in range(attempts):
        try:
            with urllib.request.urlopen(url, timeout=1) as r:
                return 200 <= r.status < 500
        except Exception:
            time.sleep(0.5)
    return False


def main() -> None:
    LOGS.mkdir(exist_ok=True)
    for name in ("api.pid", "web.pid", "realtime.pid"):
        kill_pidfile(name)
    time.sleep(0.4)

    jwt = os.environ.get("JWT_SIGNING_KEY", "local-dev-jwt-key-change-me-32b+")
    redis_url = os.environ.get("REDIS_URL", "redis://127.0.0.1:6380/0")

    api_pid = spawn(
        [str(ROOT / ".venv/bin/python"), "manage.py", "runserver", f"0.0.0.0:{API_PORT}"],
        ROOT / "backend",
        "api.log",
        "api.pid",
        {"DJANGO_SETTINGS_MODULE": "config.settings.dev"},
    )
    rt_pid = spawn(
        ["npm", "run", "dev"],
        ROOT / "realtime",
        "realtime.log",
        "realtime.pid",
        {
            "JWT_SIGNING_KEY": jwt,
            "REDIS_URL": redis_url,
            "REALTIME_EVENT_CHANNEL": "ispan:events",
            "REALTIME_CORS_ORIGINS": f"http://localhost:{WEB_PORT},http://127.0.0.1:{WEB_PORT}",
            "PORT": RT_PORT,
            "REALTIME_PORT": RT_PORT,
        },
    )
    web_pid = spawn(
        ["npm", "start", "--", "--host", "0.0.0.0", "--port", WEB_PORT],
        ROOT / "frontend",
        "web.log",
        "web.pid",
    )

    print(f"API       pid {api_pid} → http://localhost:{API_PORT}/")
    print(f"Realtime  pid {rt_pid} → http://localhost:{RT_PORT}/healthz")
    print(f"Frontend  pid {web_pid} → http://localhost:{WEB_PORT}/")

    print("API ready" if wait_url(f"http://127.0.0.1:{API_PORT}/healthz") else "API failed — see .logs/api.log")
    print(
        "Realtime ready"
        if wait_url(f"http://127.0.0.1:{RT_PORT}/healthz")
        else "Realtime failed — see .logs/realtime.log (Valkey may be down)"
    )
    print("Web ready" if wait_url(f"http://127.0.0.1:{WEB_PORT}/") else "Web failed — see .logs/web.log")


if __name__ == "__main__":
    main()
