"""
Capture full-page, high-resolution screenshots of the running app (for the report) with headless Microsoft
Edge over the Chrome DevTools Protocol. The app must be running:  streamlit run app/streamlit_app.py

Usage:  python scripts/capture_screenshots.py
Output: Visualization/app_*.png
"""
import base64
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.parse
from pathlib import Path

import requests
import websocket

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "Visualization"
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
APP = os.environ.get("QP_APP", "http://localhost:8501")
PORT = 9333
WIDTH = 1500

SHOTS = [  # (file, path, query, seconds to wait)
    ("app_overview", "", {}, 15),
    ("app_points", "points", {}, 12),
    ("app_predictor_lsg", "predictor", {"team": "LSG"}, 15),
    ("app_ask_lsg_compare", "ask", {"q": "Can Lucknow Super Giants still qualify for the top 4?", "compare": "1"}, 45),
    ("app_ask_rr_beaten", "ask", {"q": "Which teams has RR beaten and at which venues?"}, 35),
    ("app_ask_insufficient", "ask", {"q": "Who is the top run scorer for Rajasthan Royals?"}, 30),
    ("app_ask_kkr_scenario", "ask", {"q": "If KKR lose their last match, which teams are certain to finish above them?"}, 35),
    ("app_reasoner_lsg", "reasoner", {"task": "Qualification analysis (CQ5–CQ7)", "a": "LSG"}, 15),
    ("app_reasoner_rr_venues", "reasoner", {"task": "Venues played — inferred chain (CQ13)", "a": "RR"}, 15),
    ("app_graph_rr", "graph", {"team": "RR"}, 20),
    ("app_evaluation", "evaluation", {}, 15),
]


class Tab:
    def __init__(self, ws_url):
        self.ws = websocket.create_connection(ws_url, timeout=120)
        self.i = 0

    def call(self, method, **params):
        self.i += 1
        self.ws.send(json.dumps({"id": self.i, "method": method, "params": params}))
        while True:
            msg = json.loads(self.ws.recv())
            if msg.get("id") == self.i:
                return msg.get("result", {})


def main(only=None):
    profile = tempfile.mkdtemp(prefix="qp-edge-")
    edge = subprocess.Popen([EDGE, "--headless=new", f"--remote-debugging-port={PORT}", f"--user-data-dir={profile}",
                             "--hide-scrollbars", f"--window-size={WIDTH},1000", "about:blank"])
    try:
        for _ in range(50):
            try:
                requests.get(f"http://127.0.0.1:{PORT}/json/version", timeout=1)
                break
            except Exception:
                time.sleep(0.3)
        for name, path, query, wait in SHOTS:
            if only and name not in only:
                continue
            target = requests.put(f"http://127.0.0.1:{PORT}/json/new?about:blank", timeout=10).json()
            tab = Tab(target["webSocketDebuggerUrl"])
            tab.call("Page.enable")
            tab.call("Emulation.setDeviceMetricsOverride", width=WIDTH, height=1000, deviceScaleFactor=1.5, mobile=False)
            url = f"{APP}/{path}?" + urllib.parse.urlencode({**query, "nosplash": "1"})
            tab.call("Page.navigate", url=url)
            time.sleep(wait)
            h = tab.call("Runtime.evaluate", returnByValue=True, expression=(
                "Math.max(...[...document.querySelectorAll('section, div[data-testid=stMain], "
                "div[data-testid=stAppViewContainer] > section')].map(e => e.scrollHeight), "
                "document.body.scrollHeight)"))["result"]["value"]
            tab.call("Emulation.setDeviceMetricsOverride", width=WIDTH, height=int(min(h + 40, 9000)),
                     deviceScaleFactor=1.5, mobile=False)
            time.sleep(3)
            png = tab.call("Page.captureScreenshot", format="png", captureBeyondViewport=True)["data"]
            path_out = OUT / f"{name}.png"
            path_out.write_bytes(base64.b64decode(png))
            # crop the sidebar and blank margins so the report shows the page content at full size
            from PIL import Image, ImageChops
            im = Image.open(path_out).convert("RGB")
            im = im.crop((int(300 * 1.5), 0, im.width, im.height))
            bg = Image.new("RGB", im.size, im.getpixel((im.width - 5, im.height - 5)))
            box = ImageChops.difference(im, bg).getbbox()
            if box:
                im = im.crop((max(box[0] - 20, 0), max(box[1] - 20, 0), min(box[2] + 20, im.width),
                              min(box[3] + 30, im.height)))
            im.save(path_out, optimize=True)
            print(f"{name}.png  height {h}px")
            tab.ws.close()
            requests.get(f"http://127.0.0.1:{PORT}/json/close/{target['id']}", timeout=10)
    finally:
        edge.terminate()


if __name__ == "__main__":
    main(set(sys.argv[1:]) or None)
