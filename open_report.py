import argparse
import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
REPORT_DIR = PROJECT_ROOT / "reports"
STATE_FILE = PROJECT_ROOT / ".report_server.json"
REPORT_TITLE = "Allure Report"


def _is_truthy(value):
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _build_url(host, port):
    return f"http://{host}:{port}/"


def _is_report_available(url, timeout=1.5):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            if response.status != 200:
                return False
            content = response.read(512).decode("utf-8", errors="ignore")
            return REPORT_TITLE in content
    except (OSError, urllib.error.URLError):
        return False


def _load_server_state():
    if not STATE_FILE.exists():
        return None

    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _save_server_state(host, port, report_dir):
    STATE_FILE.write_text(
        json.dumps(
            {
                "host": host,
                "port": port,
                "url": _build_url(host, port),
                "report_dir": str(report_dir),
            },
            ensure_ascii=True,
            indent=2,
        ),
        encoding="utf-8",
    )


def _reuse_running_server(report_dir):
    state = _load_server_state()
    if not state:
        return None

    if state.get("report_dir") != str(report_dir):
        return None

    host = state.get("host")
    port = state.get("port")
    if not host or not isinstance(port, int):
        return None

    url = _build_url(host, port)
    if _is_report_available(url):
        return url
    return None


def _is_port_available(host, port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((host, port))
        except OSError:
            return False
    return True


def _pick_port(host, start_port, max_attempts=20):
    for port in range(start_port, start_port + max_attempts):
        if _is_port_available(host, port):
            return port
    raise RuntimeError(f"No available port found in range {start_port}-{start_port + max_attempts - 1}.")


def _creation_flags():
    flags = 0
    for name in ("CREATE_NEW_PROCESS_GROUP", "DETACHED_PROCESS"):
        flags |= getattr(subprocess, name, 0)
    return flags


def _start_server(report_dir, host, port):
    popen_kwargs = {
        "cwd": str(PROJECT_ROOT),
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
    }

    flags = _creation_flags()
    if flags:
        popen_kwargs["creationflags"] = flags

    subprocess.Popen(
        [
            sys.executable,
            "-m",
            "http.server",
            str(port),
            "-b",
            host,
            "-d",
            str(report_dir),
        ],
        **popen_kwargs,
    )


def _wait_until_ready(url, timeout=8):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if _is_report_available(url):
            return True
        time.sleep(0.2)
    return False


def open_report(host, start_port, open_browser=True):
    report_dir = REPORT_DIR.resolve()
    index_file = report_dir / "index.html"
    if not index_file.exists():
        raise FileNotFoundError(f"Report file not found: {index_file}")

    reused_url = _reuse_running_server(report_dir)
    if reused_url:
        if open_browser:
            webbrowser.open(reused_url)
        return reused_url

    port = _pick_port(host, start_port)
    _start_server(report_dir, host, port)
    url = _build_url(host, port)

    if not _wait_until_ready(url):
        raise RuntimeError(f"Report server started but did not become ready: {url}")

    _save_server_state(host, port, report_dir)

    if open_browser:
        webbrowser.open(url)
    return url


def main():
    parser = argparse.ArgumentParser(description="Serve the local Allure report over HTTP and open it in a browser.")
    parser.add_argument("--host", default=os.getenv("REPORT_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.getenv("REPORT_PORT", "8000")))
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()

    try:
        url = open_report(host=args.host, start_port=args.port, open_browser=not args.no_browser)
    except Exception as exc:
        print(f"Failed to open report: {exc}", file=sys.stderr)
        sys.exit(1)

    print(f"Allure report is available at: {url}")


if __name__ == "__main__":
    main()
