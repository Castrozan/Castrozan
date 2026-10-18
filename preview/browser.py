from contextlib import contextmanager
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
import time

from websockets.exceptions import ConnectionClosed
from websockets.sync.client import connect

from chrome import ChromeConnection


@contextmanager
def isolated_browser(theme):
    with TemporaryDirectory(prefix="readme-browser-") as directory:
        profile = Path(directory)
        with (profile / "browser.log").open("w+") as log:
            process = subprocess.Popen(
                [
                    "chromium",
                    "--headless=new",
                    "--disable-extensions",
                    "--no-first-run",
                    "--no-default-browser-check",
                    "--disable-background-networking",
                    "--remote-debugging-port=0",
                    f"--user-data-dir={profile}",
                    "about:blank",
                ],
                stdout=subprocess.DEVNULL,
                stderr=log,
            )
            try:
                endpoint_file = profile / "DevToolsActivePort"
                deadline = time.monotonic() + 15
                while not endpoint_file.exists():
                    if process.poll() is not None or time.monotonic() > deadline:
                        log.seek(0)
                        raise RuntimeError(
                            f"Isolated Chromium failed: {log.read()[:1500]}"
                        )
                    time.sleep(0.05)
                endpoint = endpoint_file.read_text().splitlines()
                with connect(
                    f"ws://127.0.0.1:{endpoint[0]}{endpoint[1]}",
                    proxy=None,
                    max_size=32 * 1024 * 1024,
                ) as connection:
                    chrome = ChromeConnection(connection)
                    try:
                        target = chrome.request(
                            "Target.createTarget", {"url": "about:blank"}
                        )
                        session = chrome.request(
                            "Target.attachToTarget", {**target, "flatten": True}
                        )
                        chrome.session_identifier = session["sessionId"]
                        chrome.request("Page.enable")
                        chrome.request(
                            "Emulation.setDeviceMetricsOverride",
                            {
                                "width": 1868,
                                "height": 973,
                                "deviceScaleFactor": 1,
                                "mobile": False,
                            },
                        )
                        chrome.request(
                            "Emulation.setAutoDarkModeOverride", {"enabled": False}
                        )
                        chrome.request(
                            "Emulation.setEmulatedMedia",
                            {
                                "features": [
                                    {"name": "prefers-color-scheme", "value": theme}
                                ]
                            },
                        )
                        chrome.request(
                            "Page.navigate", {"url": "https://github.com/Castrozan"}
                        )
                        deadline = time.monotonic() + 30
                        while not chrome.evaluate(
                            "document.readyState === 'complete' && !!document.querySelector('article.markdown-body')"
                        ):
                            if time.monotonic() > deadline:
                                raise RuntimeError(
                                    "The public GitHub profile did not load"
                                )
                            time.sleep(0.1)
                        yield chrome
                    finally:
                        if process.poll() is None:
                            chrome.session_identifier = None
                            try:
                                chrome.send("Browser.close")
                            except ConnectionClosed:
                                pass
            finally:
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()
