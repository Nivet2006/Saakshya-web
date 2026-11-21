#!/usr/bin/env python3
"""One-click cross-platform demo launcher (Windows & macOS) for ASHA Voice Field Register.

Automatically:
1. Configures UTF-8 console output (prevents Windows cp1252 Indic transcript crashes)
2. Verifies/bootstraps root `.env` and `sakshya-web-main/.env.local` (never overwrites existing)
3. Creates/repairs `backend/.venv` and installs Python dependencies if missing
4. Checks `onnxruntime` / audio drivers and surfaces clear Windows fixes if needed
5. Installs `sakshya-web-main/node_modules` if missing
6. Starts the FastAPI voice backend (:8000) and Next.js web interface (:3000)
7. Opens the browser automatically once both servers are ready and handles clean shutdown
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = ROOT_DIR / "backend"
WEB_DIR = ROOT_DIR / "sakshya-web-main"
IS_WINDOWS = sys.platform == "win32"


def ensure_utf8_stdio() -> None:
    """Force UTF-8 stdout/stderr and PYTHONUTF8=1 for Windows consoles."""
    os.environ.setdefault("PYTHONUTF8", "1")
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            with contextlib.suppress(Exception):
                reconfigure(encoding="utf-8", errors="replace")


def venv_python_path() -> Path:
    if IS_WINDOWS:
        return BACKEND_DIR / ".venv" / "Scripts" / "python.exe"
    return BACKEND_DIR / ".venv" / "bin" / "python"


def find_npm() -> str | None:
    if IS_WINDOWS:
        return shutil.which("npm.cmd") or shutil.which("npm")
    return shutil.which("npm")


def find_uv() -> str | None:
    return shutil.which("uv")


def is_port_open(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex((host, port)) == 0


def http_get_ok(url: str, timeout: float = 1.5) -> tuple[bool, str]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return resp.status == 200, body
    except Exception:
        return False, ""


def ensure_env_files() -> None:
    root_env = ROOT_DIR / ".env"
    root_example = ROOT_DIR / ".env.example"
    if not root_env.exists() and root_example.exists():
        shutil.copyfile(root_example, root_env)
        print("[SETUP] Created root .env from .env.example — remember to fill GNANI_API_KEY and GEMINI_API_KEY.")

    if root_env.exists():
        content = root_env.read_text(encoding="utf-8", errors="replace")
        for key in ("GNANI_API_KEY", "GEMINI_API_KEY"):
            for line in content.splitlines():
                stripped = line.strip()
                if stripped.startswith(f"{key}="):
                    val = stripped.split("=", 1)[1].split("#", 1)[0].strip()
                    if not val or val.startswith("your_"):
                        print(f"[WARN] {key} in .env looks empty or placeholder; live voice/LLM calls need real keys.")
                    break

    web_env_local = WEB_DIR / ".env.local"
    if WEB_DIR.exists() and not web_env_local.exists():
        web_env_local.write_text(
            "NODE_ENV=development\n"
            "NEXT_PUBLIC_APP_URL=http://localhost:3000\n"
            "NEXT_PUBLIC_VOICE_API_BASE_URL=http://localhost:8000\n"
            "NEXT_PUBLIC_VOICE_WS_URL=ws://localhost:8000\n"
            "NEXT_PUBLIC_DEFAULT_LANGUAGE=hi-IN\n"
            "NEXT_PUBLIC_SUPPORTED_LANGUAGES=hi-IN,kn-IN,ta-IN,te-IN,ml-IN,bn-IN,mr-IN,gu-IN,pa-IN,en-IN\n"
            "NEXT_PUBLIC_SYNTHETIC_DATA_ONLY=true\n",
            encoding="utf-8",
        )
        print("[SETUP] Created sakshya-web-main/.env.local with local backend defaults.")


def run_checked(cmd: list[str], *, cwd: Path, label: str) -> None:
    print(f"[{label}] Running: {' '.join(cmd)}")
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    proc = subprocess.run(cmd, cwd=str(cwd), env=env)
    if proc.returncode != 0:
        raise RuntimeError(f"[{label}] Command failed with exit code {proc.returncode}")


def ensure_backend_venv() -> Path:
    vpy = venv_python_path()
    uv_bin = find_uv()
    req_file = BACKEND_DIR / "requirements.txt"

    if not vpy.exists():
        print("[SETUP] Creating Python virtual environment in backend/.venv ...")
        if uv_bin:
            run_checked(
                [uv_bin, "venv", str(BACKEND_DIR / ".venv"), "--python", "3.12"],
                cwd=ROOT_DIR,
                label="SETUP",
            )
        else:
            run_checked(
                [sys.executable, "-m", "venv", str(BACKEND_DIR / ".venv")],
                cwd=ROOT_DIR,
                label="SETUP",
            )
        install_backend_deps(vpy, uv_bin, req_file)

    # Probe required modules and auto-repair missing packages
    probe_cmd = [
        str(vpy),
        "-c",
        (
            "import fastapi, uvicorn, websockets, pydantic_settings, "
            "sounddevice, numpy, onnxruntime, gnani, pipecat_gnani, app.main; "
            "print('OK')"
        ),
    ]
    probe = subprocess.run(
        probe_cmd,
        cwd=str(BACKEND_DIR),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if probe.returncode != 0:
        stderr = (probe.stderr or "") + (probe.stdout or "")
        if IS_WINDOWS and ("DLL load failed" in stderr or "onnxruntime_pybind11_state" in stderr):
            raise RuntimeError(
                "Windows missing Microsoft Visual C++ Redistributable for onnxruntime.\n"
                "Download & install: https://aka.ms/vs/17/release/vc_redist.x64.exe\n"
                f"Details: {stderr.strip()}"
            )
        print("[SETUP] Installing/repairing backend Python dependencies...")
        install_backend_deps(vpy, uv_bin, req_file)

        probe2 = subprocess.run(
            probe_cmd,
            cwd=str(BACKEND_DIR),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if probe2.returncode != 0:
            raise RuntimeError(f"Backend environment check failed:\n{probe2.stderr or probe2.stdout}")

    return vpy


def install_backend_deps(vpy: Path, uv_bin: str | None, req_file: Path) -> None:
    if uv_bin:
        run_checked(
            [uv_bin, "pip", "install", "--python", str(vpy), "-r", str(req_file)],
            cwd=ROOT_DIR,
            label="PIP",
        )
    else:
        run_checked(
            [str(vpy), "-m", "pip", "install", "--upgrade", "pip"],
            cwd=ROOT_DIR,
            label="PIP",
        )
        run_checked(
            [str(vpy), "-m", "pip", "install", "-r", str(req_file)],
            cwd=ROOT_DIR,
            label="PIP",
        )


def ensure_web_deps(npm_bin: str) -> None:
    if not WEB_DIR.exists():
        raise RuntimeError(f"Web directory not found: {WEB_DIR}")
    node_modules = WEB_DIR / "node_modules"
    if not node_modules.exists():
        print("[SETUP] Installing Next.js dependencies in sakshya-web-main/ (first run only)...")
        run_checked([npm_bin, "install"], cwd=WEB_DIR, label="NPM")


def stream_output(proc: subprocess.Popen[str], prefix: str) -> None:
    if proc.stdout is None:
        return
    try:
        for line in proc.stdout:
            print(f"[{prefix}] {line.rstrip()}")
    except Exception:
        pass


def spawn_service(cmd: list[str], *, cwd: Path, prefix: str) -> subprocess.Popen[str]:
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONUNBUFFERED"] = "1"
    popen_kwargs: dict[str, object] = {
        "cwd": str(cwd),
        "env": env,
        "stdout": subprocess.PIPE,
        "stderr": subprocess.STDOUT,
        "text": True,
        "encoding": "utf-8",
        "errors": "replace",
        "bufsize": 1,
    }
    if IS_WINDOWS:
        popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP  # type: ignore[attr-defined]
    else:
        popen_kwargs["start_new_session"] = True

    proc = subprocess.Popen(cmd, **popen_kwargs)  # type: ignore[arg-type]
    t = threading.Thread(target=stream_output, args=(proc, prefix), daemon=True)
    t.start()
    return proc


def terminate_process_tree(proc: subprocess.Popen[str], name: str) -> None:
    if proc.poll() is not None:
        return
    print(f"[STOP] Stopping {name} (pid={proc.pid})...")
    try:
        if IS_WINDOWS:
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                capture_output=True,
                timeout=10,
            )
        else:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            proc.wait(timeout=5)
    except Exception:
        with contextlib.suppress(Exception):
            proc.kill()


def wait_for_http(url: str, *, proc: subprocess.Popen[str] | None, name: str, timeout_s: float) -> bool:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if proc is not None and proc.poll() is not None:
            raise RuntimeError(f"{name} exited prematurely with code {proc.returncode}")
        ok, _ = http_get_ok(url, timeout=1.0)
        if ok:
            return True
        time.sleep(0.5)
    return False


def main() -> int:
    ensure_utf8_stdio()
    parser = argparse.ArgumentParser(description="One-click ASHA Voice Field Register Demo Launcher")
    parser.add_argument("--backend-port", type=int, default=8000, help="FastAPI backend port (default: 8000)")
    parser.add_argument("--web-port", type=int, default=3000, help="Next.js web port (default: 3000)")
    parser.add_argument("--no-browser", action="store_true", help="Do not auto-open the web browser")
    parser.add_argument("--with-cli", action="store_true", help="Also launch local CLI microphone test client")
    parser.add_argument("--check-only", action="store_true", help="Verify environment/dependencies and exit")
    args = parser.parse_args()

    print("============================================================")
    print("  ASHA Voice Field Register — One-Click Demo Launcher")
    print(f"  Platform: {sys.platform} | Python: {sys.version.split()[0]}")
    print("============================================================")

    ensure_env_files()
    vpy = ensure_backend_venv()

    npm_bin = find_npm()
    if not npm_bin:
        raise RuntimeError(
            "Node.js / npm not found in PATH. Install Node.js LTS (https://nodejs.org/) and retry."
        )
    ensure_web_deps(npm_bin)

    if args.check_only:
        print("[OK] Preflight checks passed! Ready to launch.")
        return 0

    children: list[tuple[str, subprocess.Popen[str]]] = []
    backend_url = f"http://127.0.0.1:{args.backend_port}/health"
    web_url = f"http://localhost:{args.web_port}"

    try:
        # 1. Start Voice Backend
        healthy, _ = http_get_ok(backend_url)
        if healthy:
            print(f"[BACKEND] Reusing existing healthy backend at http://127.0.0.1:{args.backend_port}")
            backend_proc = None
        elif is_port_open("127.0.0.1", args.backend_port):
            raise RuntimeError(
                f"Port {args.backend_port} is already in use by another process. "
                f"Stop it or pass --backend-port <port>."
            )
        else:
            print(f"[BACKEND] Starting FastAPI Voice Engine on port {args.backend_port}...")
            backend_proc = spawn_service(
                [
                    str(vpy),
                    "-m",
                    "uvicorn",
                    "app.main:app",
                    "--host",
                    "0.0.0.0",
                    "--port",
                    str(args.backend_port),
                ],
                cwd=BACKEND_DIR,
                prefix="BACKEND",
            )
            children.append(("Voice Backend", backend_proc))
            if not wait_for_http(backend_url, proc=backend_proc, name="Voice Backend", timeout_s=45.0):
                raise RuntimeError("Voice Backend did not become ready within 45s.")
            _, health_body = http_get_ok(backend_url)
            with contextlib.suppress(Exception):
                h = json.loads(health_body)
                print(
                    f"[BACKEND] Ready! stt={h.get('stt_model')} tts={h.get('tts_model')} "
                    f"llm={h.get('llm_model')} live_creds={h.get('live_credentials_configured')}"
                )

        # 2. Start Web UI
        web_up, _ = http_get_ok(f"http://127.0.0.1:{args.web_port}")
        if web_up:
            print(f"[WEB] Reusing existing web UI at {web_url}")
            web_proc = None
        elif is_port_open("127.0.0.1", args.web_port):
            raise RuntimeError(
                f"Port {args.web_port} is already in use by another process. "
                f"Stop it or pass --web-port <port>."
            )
        else:
            print(f"[WEB] Starting Next.js Web Interface on port {args.web_port}...")
            web_proc = spawn_service(
                [npm_bin, "run", "dev", "--", "--port", str(args.web_port)],
                cwd=WEB_DIR,
                prefix="WEB",
            )
            children.append(("Web UI", web_proc))
            if not wait_for_http(
                f"http://127.0.0.1:{args.web_port}", proc=web_proc, name="Web UI", timeout_s=60.0
            ):
                raise RuntimeError("Next.js Web UI did not become ready within 60s.")
            print(f"[WEB] Ready at {web_url}")

        # 3. Optional CLI microphone client
        if args.with_cli:
            cli_proc = spawn_service(
                [
                    str(vpy),
                    str(BACKEND_DIR / "cli_client.py"),
                    "--server",
                    f"ws://127.0.0.1:{args.backend_port}",
                    "--language",
                    "indic-auto",
                ],
                cwd=ROOT_DIR,
                prefix="CLI",
            )
            children.append(("CLI Client", cli_proc))

        if not args.no_browser:
            print(f"[DEMO] Opening browser at {web_url} ...")
            webbrowser.open(web_url)

        print("============================================================")
        print(f"  DEMO LIVE -> Web UI:  {web_url}")
        print(f"               Voice:   http://127.0.0.1:{args.backend_port}/health")
        print("  Press Ctrl+C to stop all services cleanly.")
        print("============================================================")

        while True:
            for name, proc in children:
                code = proc.poll()
                if code is not None:
                    raise RuntimeError(f"{name} stopped unexpectedly (exit code {code}).")
            time.sleep(1.0)

    except KeyboardInterrupt:
        print("\n[DEMO] Shutdown requested...")
        return 0
    except Exception as exc:
        print(f"\n[ERROR] {exc}", file=sys.stderr)
        return 1
    finally:
        for name, proc in reversed(children):
            terminate_process_tree(proc, name)


if __name__ == "__main__":
    sys.exit(main())
