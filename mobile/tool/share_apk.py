"""Share a locally built APK on the Wi-Fi network via a QR code.

Copies the newest debug APK into mobile/dist/ and writes an index.html with a QR code
pointing at it, plus qr.png. Serve mobile/dist/ with any static server bound to 0.0.0.0
(see the "apk-share" entry in .claude/launch.json), then scan the QR with the phone.

Usage: python mobile/tool/share_apk.py <lan-ip> [port]
Requires: pip install segno
"""

import html
import shutil
import sys
from datetime import datetime
from pathlib import Path

import segno

MOBILE = Path(__file__).resolve().parents[1]
APK_DIR = MOBILE / "build" / "app" / "outputs" / "flutter-apk"
DIST = MOBILE / "dist"
APK_NAME = "food-omniscan-debug.apk"


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit("usage: share_apk.py <lan-ip> [port]")
    ip, port = sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 8090
    apks = sorted(APK_DIR.glob("*.apk"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not apks:
        sys.exit(f"No APK found in {APK_DIR}. Run flutter build apk first.")
    DIST.mkdir(exist_ok=True)
    shutil.copy2(apks[0], DIST / APK_NAME)
    size_mb = (DIST / APK_NAME).stat().st_size / 1_048_576

    url = f"http://{ip}:{port}/{APK_NAME}"
    qr = segno.make(url, error="m")
    qr.save(DIST / "qr.png", scale=12, border=3, dark="#134E4A")
    svg = qr.svg_inline(scale=10, dark="#134E4A")
    built = datetime.fromtimestamp(apks[0].stat().st_mtime).strftime("%b %d, %Y %I:%M %p")

    (DIST / "index.html").write_text(
        f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Food omniScan test build</title>
<style>
body{{font-family:system-ui,sans-serif;background:#f6f8f7;color:#0f1f1c;margin:0;padding:24px;display:flex;justify-content:center}}
main{{max-width:420px;text-align:center}}
.card{{background:#fff;border:1px solid #dde5e2;border-radius:20px;padding:24px;margin-top:16px}}
a.btn{{display:inline-block;background:#0f766e;color:#fff;padding:14px 22px;border-radius:14px;font-weight:700;text-decoration:none;margin-top:12px}}
small{{color:#5b6b67}} ol{{text-align:left;line-height:1.6}}
</style></head>
<body><main>
<h1>Food omniScan</h1><p>Android test build (debug, arm64) · {size_mb:.0f} MB · built {html.escape(built)}</p>
<div class="card">{svg}<p><small>Scan with your phone's camera</small></p>
<a class="btn" href="/{APK_NAME}" download>Download APK</a></div>
<div class="card"><ol>
<li>Phone and this computer must be on the same Wi-Fi.</li>
<li>Open the download, then allow your browser to install unknown apps when Android asks.</li>
<li>This is a test build signed with a debug key, so it may show a Play Protect warning.</li>
</ol><small>{html.escape(url)}</small></div>
</main></body></html>
""",
        encoding="utf-8",
    )
    print(url)
    print(f"Page: http://{ip}:{port}/  ({size_mb:.0f} MB APK)")


if __name__ == "__main__":
    main()
