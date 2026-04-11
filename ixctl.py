"""Investment-X launcher — single CLI for dev + prod.

Named ``ixctl`` (not ``ix``) so it doesn't shadow the top-level ``ix``
package when Python resolves imports from the repo root.

Usage::

    python ixctl.py dev             # dev mode (reload, no build), both sides
    python ixctl.py dev be          # backend only
    python ixctl.py dev fe          # frontend only
    python ixctl.py prod            # prod mode (built frontend, no reload)
    python ixctl.py prod --check    # prod + wait for backend /health
    python ixctl.py build           # next build
    python ixctl.py stop            # kill backend + frontend + tunnel

Design notes:
    * Stdlib-only (argparse, subprocess, urllib). No new deps.
    * dev and prod share ports 3000/8000 — stop + restart is the only model.
    * spawn() opens each server in its own Windows Terminal tab (falls back
      to cmd if wt isn't installed), matching the prior .bat workflow.
    * ensure_db() starts postgresql-x64-17 if it isn't running.
    * load_env() parses .env for the Cloudflare tunnel token and tolerates
      quoted values, blank lines, and comments.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import Literal

ROOT = Path(__file__).resolve().parent
UI_DIR = ROOT / "ui"

FRONTEND_PORT = 3000
BACKEND_PORT = 8000
POSTGRES_SVC = "postgresql-x64-17"


# ─────────────────────────────────────────────────────────────────────
# Logging
# ─────────────────────────────────────────────────────────────────────


def log(msg: str) -> None:
    print(f"[ix] {msg}", flush=True)


# ─────────────────────────────────────────────────────────────────────
# Process + port helpers
# ─────────────────────────────────────────────────────────────────────


def kill_port(port: int) -> None:
    """Kill any process LISTENING on the given port (Windows only)."""
    try:
        out = subprocess.run(
            ["netstat", "-ano"],
            capture_output=True, text=True, check=False,
        ).stdout
    except FileNotFoundError:
        return
    pids: set[str] = set()
    needle = f":{port}"
    for line in out.splitlines():
        parts = line.split()
        if len(parts) < 5 or "LISTENING" not in parts:
            continue
        if any(p.endswith(needle) for p in parts[:-1]):
            pids.add(parts[-1])
    for pid in pids:
        subprocess.run(
            ["taskkill", "/F", "/PID", pid],
            capture_output=True, check=False,
        )
        log(f"killed pid {pid} on port {port}")


def kill_tunnel() -> None:
    subprocess.run(
        ["taskkill", "/F", "/IM", "cloudflared.exe"],
        capture_output=True, check=False,
    )


def ensure_db() -> None:
    """Start the postgres service if it isn't already running."""
    r = subprocess.run(
        ["sc", "query", POSTGRES_SVC],
        capture_output=True, text=True, check=False,
    )
    if "RUNNING" in r.stdout:
        log(f"postgres ({POSTGRES_SVC}) already running")
        return
    log(f"starting postgres service {POSTGRES_SVC}")
    r = subprocess.run(
        ["net", "start", POSTGRES_SVC],
        capture_output=True, text=True, check=False,
    )
    if r.returncode != 0:
        log(f"  WARN: net start failed — may need admin shell")


# ─────────────────────────────────────────────────────────────────────
# .env parsing (stdlib)
# ─────────────────────────────────────────────────────────────────────


def load_env() -> dict[str, str]:
    env: dict[str, str] = {}
    path = ROOT / ".env"
    if not path.exists():
        return env
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k = k.strip()
        v = v.strip()
        if len(v) >= 2 and v[0] == v[-1] and v[0] in ("'", '"'):
            v = v[1:-1]
        env[k] = v
    return env


# ─────────────────────────────────────────────────────────────────────
# Spawning new terminal windows
# ─────────────────────────────────────────────────────────────────────


def spawn(title: str, cwd: Path, cmd: list[str]) -> None:
    """Open a new terminal window running ``cmd`` in ``cwd``.

    Prefers Windows Terminal (``wt``) when available so each service gets
    its own titled tab; falls back to plain ``cmd /k`` otherwise.
    """
    cmd_str = subprocess.list2cmdline(cmd)
    if shutil.which("wt"):
        subprocess.Popen(
            ["wt", "-d", str(cwd), "--title", title,
             "--", "cmd", "/k", cmd_str],
            close_fds=True,
        )
    else:
        subprocess.Popen(
            ["cmd", "/c", "start", title, "cmd", "/k",
             f"cd /d {cwd} && {cmd_str}"],
            close_fds=True,
        )


# ─────────────────────────────────────────────────────────────────────
# Service launchers
# ─────────────────────────────────────────────────────────────────────


Mode = Literal["dev", "prod"]


def launch_backend(mode: Mode) -> None:
    cmd = [
        sys.executable, "-m", "uvicorn", "ix.api.main:app",
        "--host", "127.0.0.1", "--port", str(BACKEND_PORT),
    ]
    if mode == "dev":
        cmd += ["--reload", "--reload-dir", "ix"]
    else:
        cmd += ["--workers", "1"]
    spawn(f"IX Backend ({mode})", ROOT, cmd)


def launch_frontend(mode: Mode) -> None:
    if mode == "dev":
        cmd = ["npx", "next", "dev", "-p", str(FRONTEND_PORT)]
    else:
        cmd = ["npx", "next", "start", "-p", str(FRONTEND_PORT)]
    spawn(f"IX Frontend ({mode})", UI_DIR, cmd)


def launch_tunnel() -> None:
    token = load_env().get("CLOUDFLARE_TUNNEL_TOKEN")
    if not token:
        log("  WARN: CLOUDFLARE_TUNNEL_TOKEN missing in .env, skipping tunnel")
        return
    spawn(
        "IX Tunnel",
        ROOT,
        ["cloudflared", "tunnel", "--no-autoupdate", "run", "--token", token],
    )


def ensure_build() -> None:
    build_id = UI_DIR / ".next" / "BUILD_ID"
    if build_id.exists():
        return
    log("no frontend build found → running `next build`")
    r = subprocess.run(["npx", "next", "build"], cwd=UI_DIR)
    if r.returncode != 0:
        log("  ERROR: next build failed")
        sys.exit(r.returncode)


# ─────────────────────────────────────────────────────────────────────
# Health check
# ─────────────────────────────────────────────────────────────────────


def health_check(url: str, timeout: int = 30) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as resp:
                if resp.status < 500:
                    return True
        except Exception:
            pass
        time.sleep(1)
    return False


# ─────────────────────────────────────────────────────────────────────
# Commands
# ─────────────────────────────────────────────────────────────────────


def _stop_all() -> None:
    kill_port(FRONTEND_PORT)
    kill_port(BACKEND_PORT)
    kill_tunnel()


def _run(mode: Mode, target: str, *, check: bool, skip_stop: bool) -> int:
    log(f"{mode} mode — target={target}")
    if not skip_stop:
        _stop_all()
    ensure_db()
    if mode == "prod":
        ensure_build()

    if target in ("both", "be"):
        launch_backend(mode)
    if target in ("both", "fe"):
        launch_frontend(mode)
    if target == "both":
        launch_tunnel()

    log(f"App: http://localhost:{FRONTEND_PORT}")
    log(f"API: http://localhost:{BACKEND_PORT}/docs")
    if mode == "prod":
        log("Tunnel: investment-x.app")

    if check:
        log("health check: polling backend /health ...")
        ok = health_check(
            f"http://127.0.0.1:{BACKEND_PORT}/health",
            timeout=60 if mode == "prod" else 30,
        )
        log(f"  backend: {'OK' if ok else 'DOWN'}")
        return 0 if ok else 1
    return 0


def cmd_dev(args: argparse.Namespace) -> int:
    return _run("dev", args.target, check=args.check, skip_stop=args.no_stop)


def cmd_prod(args: argparse.Namespace) -> int:
    return _run("prod", args.target, check=args.check, skip_stop=args.no_stop)


def cmd_build(args: argparse.Namespace) -> int:
    log("building frontend (next build)")
    r = subprocess.run(["npx", "next", "build"], cwd=UI_DIR)
    return r.returncode


def cmd_stop(args: argparse.Namespace) -> int:
    log("stopping backend + frontend + tunnel (db left running)")
    _stop_all()
    return 0


# ─────────────────────────────────────────────────────────────────────
# Argparse wiring
# ─────────────────────────────────────────────────────────────────────


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="ixctl",
        description="Investment-X launcher — dev, prod, build, stop.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    for name, fn in (("dev", cmd_dev), ("prod", cmd_prod)):
        sp = sub.add_parser(name, help=f"Run in {name} mode")
        sp.add_argument(
            "target", nargs="?", default="both",
            choices=("both", "be", "fe"),
            help="which side to start (default: both)",
        )
        sp.add_argument(
            "--no-stop", action="store_true",
            help="skip killing existing processes on 3000/8000",
        )
        sp.add_argument(
            "--check", action="store_true",
            help="after launch, poll /health and fail if backend is down",
        )
        sp.set_defaults(func=fn)

    sp = sub.add_parser("build", help="Build the frontend (next build)")
    sp.set_defaults(func=cmd_build)

    sp = sub.add_parser("stop", help="Stop backend + frontend + tunnel")
    sp.set_defaults(func=cmd_stop)

    return p


def main() -> int:
    args = build_parser().parse_args()
    return int(args.func(args) or 0)


if __name__ == "__main__":
    sys.exit(main())
