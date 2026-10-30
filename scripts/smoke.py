"""Run after npm run build. Verifies local API/frontend wiring without a database."""

import os
import subprocess
import sys
import time
from pathlib import Path
from shutil import which

import httpx
from bs4 import BeautifulSoup

root = Path(__file__).resolve().parents[1]
env = dict(os.environ, BACKEND_URL="http://127.0.0.1:18000")
processes = []
try:
    processes.append(
        subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "app.main:app",
                "--app-dir",
                "backend",
                "--host",
                "127.0.0.1",
                "--port",
                "18000",
            ],
            cwd=root,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    )
    processes.append(
        subprocess.Popen(
            [
                which("npm") or "npm",
                "run",
                "start",
                "--",
                "--hostname",
                "127.0.0.1",
                "--port",
                "13000",
            ],
            cwd=root / "frontend",
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    )
    with httpx.Client(trust_env=False, timeout=15) as client:
        for base in ["http://127.0.0.1:18000/health/live", "http://127.0.0.1:13000"]:
            deadline = time.monotonic() + 25
            while True:
                try:
                    response = client.get(base)
                    assert response.status_code == 200
                    break
                except httpx.ConnectError:
                    if time.monotonic() >= deadline:
                        raise RuntimeError("Local process did not start") from None
                    time.sleep(0.2)
        response = client.get("http://127.0.0.1:18000/health/ready")
        assert response.status_code in {200, 503}
        page = BeautifulSoup(client.get("http://127.0.0.1:13000").text, "html.parser")
        text = page.get_text(" ", strip=True)
        assert "Ready: Available" in text
        assert "Research data pending" in text
        if response.status_code == 503:
            assert "Pending:" in text
        print("PASS: live API, readiness state, production frontend and real health wiring")
finally:
    for process in reversed(processes):
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
