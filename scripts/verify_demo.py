"""Start both local apps and exercise them with Playwright in one process tree.

Requires both Python packages installed and Playwright/Chromium available.
"""
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def ready(port):
    for _ in range(60):
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=1) as response:
                if response.status == 200:
                    return
        except (OSError, urllib.error.URLError):
            time.sleep(.2)
    raise RuntimeError(f"Local server on {port} did not start")


def main():
    servers = []
    try:
        for module, port in [("agent_platform", 8011), ("healthcare_rag", 8012)]:
            servers.append(subprocess.Popen([sys.executable, "-m", "uvicorn", f"{module}.api:app",
                                            "--host", "127.0.0.1", "--port", str(port), "--log-level", "error"],
                                           env={**os.environ, "OPENBLAS_NUM_THREADS": "1"}))
            ready(port)
        subprocess.run(["node", str(ROOT / "scripts/verify_browser.cjs")], cwd=ROOT, check=True)
    finally:
        for server in servers:
            server.terminate()
        for server in servers:
            server.wait(timeout=10)


if __name__ == "__main__":
    main()
