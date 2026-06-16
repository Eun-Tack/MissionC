"""MissionC tray launcher for Windows."""

import subprocess
import sys
import threading
import time
import traceback
import webbrowser
import os
from pathlib import Path

ROOT = Path(__file__).parent
URL = "http://127.0.0.1:8000"
LOG_DIR = ROOT / "data"
SERVER_LOG = LOG_DIR / "mc_server.log"
TRAY_LOG = LOG_DIR / "mc_tray.log"
_LOCK_HANDLE = None


def _log(message):
    LOG_DIR.mkdir(exist_ok=True)
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(TRAY_LOG, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {message}\n")


def _acquire_single_instance():
    """Keep one tray icon; later launches just open the existing app."""
    import msvcrt

    global _LOCK_HANDLE
    LOG_DIR.mkdir(exist_ok=True)
    _LOCK_HANDLE = open(LOG_DIR / "mc_tray.lock", "a+b")
    try:
        msvcrt.locking(_LOCK_HANDLE.fileno(), msvcrt.LK_NBLCK, 1)
        return True
    except OSError:
        return False


def _make_icon():
    from PIL import Image, ImageDraw, ImageFont

    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([0, 0, 63, 63], radius=14, fill=(108, 60, 210, 255))
    try:
        font = ImageFont.truetype("arialbd.ttf", 36)
    except Exception:
        font = ImageFont.load_default()
    draw.text((32, 32), "M", fill="white", font=font, anchor="mm")
    return img


def _server_running():
    import urllib.request

    try:
        urllib.request.urlopen(f"{URL}/health", timeout=1)
        return True
    except Exception:
        return False


def _wait_and_open():
    import urllib.request

    for _ in range(30):
        time.sleep(1)
        try:
            urllib.request.urlopen(f"{URL}/health", timeout=1)
            break
        except Exception:
            continue
    webbrowser.open(f"{URL}/?fresh={int(time.time())}")


def main():
    try:
        if not _acquire_single_instance():
            webbrowser.open(f"{URL}/?fresh={int(time.time())}")
            return

        try:
            import pystray
            from PIL import Image  # noqa: F401
        except ImportError:
            import tkinter.messagebox as mb

            mb.showerror("MissionC", "pystray / Pillow is missing.\nRun: pip install pystray Pillow")
            sys.exit(1)

        server = None
        if not _server_running():
            LOG_DIR.mkdir(exist_ok=True)
            server_log = open(SERVER_LOG, "a", encoding="utf-8")
            server_log.write(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] Starting MissionC server\n")
            server_log.flush()
            server = subprocess.Popen(
                [sys.executable, str(ROOT / "run.py")],
                cwd=str(ROOT),
                env={**os.environ, "MC_ENV": "production"},
                stdout=server_log,
                stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            _log(f"Started server process pid={server.pid}")

        threading.Thread(target=_wait_and_open, daemon=True).start()

        def on_open(icon, item):
            webbrowser.open(f"{URL}/?fresh={int(time.time())}")

        def on_quit(icon, item):
            if server:
                server.terminate()
            icon.stop()

        icon = pystray.Icon(
            "MissionC",
            _make_icon(),
            "MissionC",
            menu=pystray.Menu(
                pystray.MenuItem("Open MissionC", on_open, default=True),
                pystray.MenuItem("Quit", on_quit),
            ),
        )
        icon.run()
    except Exception:
        _log(traceback.format_exc())
        raise


if __name__ == "__main__":
    main()
