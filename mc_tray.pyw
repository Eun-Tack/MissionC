"""
MC — Mission Control tray launcher (Windows)
더블클릭으로 시작. 트레이 아이콘 좌클릭: 브라우저 열기, 우클릭: 종료.
"""
import subprocess
import sys
import threading
import time
import webbrowser
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).parent
URL  = "http://localhost:8000"


def _make_icon():
    from PIL import Image, ImageDraw, ImageFont
    img  = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([0, 0, 63, 63], radius=14,
                           fill=(108, 60, 210, 255))
    try:
        font = ImageFont.truetype("arialbd.ttf", 36)
    except Exception:
        font = ImageFont.load_default()
    draw.text((32, 32), "M", fill="white", font=font, anchor="mm")
    return img


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


def _server_running():
    import urllib.request
    try:
        urllib.request.urlopen(f"{URL}/health", timeout=1)
        return True
    except Exception:
        return False


def main():
    try:
        import pystray
        from PIL import Image
    except ImportError:
        import tkinter.messagebox as mb
        mb.showerror("MC", "pystray / Pillow 미설치\npip install pystray Pillow")
        sys.exit(1)

    # Start server process only if one is not already listening.
    server = None
    if not _server_running():
        server = subprocess.Popen(
            [sys.executable, str(ROOT / "run.py")],
            cwd=str(ROOT),
            creationflags=subprocess.CREATE_NO_WINDOW,
        )

    # Open browser after server warms up
    threading.Thread(target=_wait_and_open, daemon=True).start()

    def on_open(icon, item):
        webbrowser.open(f"{URL}/?fresh={int(time.time())}")

    def on_quit(icon, item):
        if server:
            server.terminate()
        icon.stop()

    icon = pystray.Icon(
        "MC",
        _make_icon(),
        "MC — Mission Control",
        menu=pystray.Menu(
            pystray.MenuItem("열기  localhost:8000", on_open, default=True),
            pystray.MenuItem("종료", on_quit),
        ),
    )
    icon.run()


if __name__ == "__main__":
    main()
