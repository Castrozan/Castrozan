import base64
import io
import json
from pathlib import Path
import subprocess
import sys
import time

from PIL import Image, ImageChops

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "preview"))
from browser import isolated_browser


def image_details(chrome):
    deadline = time.monotonic() + 10
    while True:
        details = chrome.evaluate("""(() => {
          const image=[...document.querySelectorAll('article img[src*=".gif"]')].find(image=>image.getBoundingClientRect().width>0);
          if (!image) return null;
          const bounds=image.getBoundingClientRect();
          return {source:image.currentSrc,complete:image.complete,width:image.naturalWidth,height:image.naturalHeight,clip:{x:bounds.left+scrollX,y:bounds.top+scrollY,width:bounds.width,height:bounds.height,scale:1}};
        })()""")
        if details and details["complete"] and details["clip"]["width"] == 846:
            return details
        if time.monotonic() > deadline:
            raise TimeoutError(f"Visible GIF layout did not settle: {details}")
        time.sleep(0.1)


root = Path(__file__).resolve().parents[2]
revision = subprocess.check_output(
    ["git", "rev-parse", "HEAD"], cwd=root, text=True
).strip()
results = []
for name in ["native-max", "native-hour"]:
    with isolated_browser("dark") as chrome:
        chrome.request(
            "Emulation.setDeviceMetricsOverride",
            {"width": 1280, "height": 973, "deviceScaleFactor": 1, "mobile": False},
        )
        chrome.request("Network.enable")
        chrome.request("Network.setCacheDisabled", {"cacheDisabled": True})
        started = time.monotonic()
        chrome.request(
            "Page.navigate",
            {
                "url": f"https://github.com/Castrozan/Castrozan/tree/{revision}/stress/{name}"
            },
        )
        deadline = started + 120
        while not chrome.evaluate(
            f"location.pathname.endsWith('/{name}') && document.readyState==='complete' && !!document.querySelector('article img[src*=\\\".gif\\\"]')"
        ):
            if time.monotonic() > deadline:
                raise TimeoutError(name)
            time.sleep(0.1)
        chrome.evaluate("document.fonts.ready.then(()=>true)")
        details = image_details(chrome)
        details["name"] = name
        details["load_seconds"] = round(time.monotonic() - started, 3)
        if (details["width"], details["height"]) != (846, 996):
            raise AssertionError(details)
        samples = []
        for index in range(2):
            clip = image_details(chrome)["clip"]
            screenshot = chrome.request(
                "Page.captureScreenshot",
                {"format": "png", "captureBeyondViewport": True, "clip": clip},
            )
            with Image.open(io.BytesIO(base64.b64decode(screenshot["data"]))) as image:
                samples.append(image.convert("RGB"))
            if index == 0:
                time.sleep(0.7)
        red, green, blue = ImageChops.difference(*samples).split()
        difference = ImageChops.lighter(ImageChops.lighter(red, green), blue)
        details["motion_changed_pixels"] = (
            difference.width * difference.height - difference.histogram()[0]
        )
        if details["motion_changed_pixels"] < 100:
            raise AssertionError(details)
        results.append(details)
        print(json.dumps(details), flush=True)
(root / "stress/native-max/browser-verification.json").write_text(
    json.dumps(results, indent=2) + "\n"
)
