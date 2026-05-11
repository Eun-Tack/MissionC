"""Development server launcher — runs migrate then starts core-api."""

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent
PROD = os.environ.get("MC_ENV", "development") == "production"


def main():
    # 1. Ensure DB is initialized
    result = subprocess.run([sys.executable, str(ROOT / "migrate.py")], cwd=ROOT)
    if result.returncode != 0:
        print("[run.py] migrate.py failed — aborting.", file=sys.stderr)
        sys.exit(1)

    # 2. Start core-api with uvicorn
    host = os.environ.get("HOST", "0.0.0.0")
    port = os.environ.get("PORT", "8000")
    print(f"[run.py] Starting MC core-api at http://{host}:{port}  (env={os.environ.get('MC_ENV','development')})")

    cmd = [
        sys.executable, "-m", "uvicorn",
        "src.core_api.main:app",
        "--host", host,
        "--port", port,
    ]
    if not PROD:
        cmd += ["--reload", "--reload-dir", str(ROOT / "src")]

    subprocess.run(cmd, cwd=ROOT)


if __name__ == "__main__":
    main()
