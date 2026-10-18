import argparse
import base64
import io
import json
from pathlib import Path
import time

from markdown_it import MarkdownIt
from PIL import Image
from websockets.sync.client import connect

from chrome import ChromeConnection
from encode import encode_recording
from render import read_recording, render_turns


def record_frames(chrome, destination, width, height):
    frames = [(destination / "front.png", 0.0)]
    started = time.monotonic()
    first_timestamp = None
    viewport = chrome.evaluate("({width: innerWidth, height: innerHeight})")
    chrome.evaluate("window.profileReadmeCard.animation.play()")
    chrome.request(
        "Page.startScreencast",
        {
            "format": "png",
            "maxWidth": viewport["width"],
            "maxHeight": viewport["height"],
            "everyNthFrame": 3,
        },
    )
    try:
        while time.monotonic() - started < 20.3:
            try:
                response = json.loads(chrome.connection.recv(timeout=1))
            except TimeoutError:
                continue
            if response.get("method") != "Page.screencastFrame":
                continue
            if response.get("sessionId") != chrome.session_identifier:
                continue
            parameters = response["params"]
            chrome.send(
                "Page.screencastFrameAck", {"sessionId": parameters["sessionId"]}
            )
            timestamp = parameters["metadata"]["timestamp"]
            if first_timestamp is None:
                first_timestamp = timestamp
            elapsed = max(0.0, timestamp - first_timestamp)
            if elapsed > 20:
                break
            destination_path = destination / f"frame-{len(frames):05d}.png"
            with Image.open(io.BytesIO(base64.b64decode(parameters["data"]))) as image:
                image.crop((0, 0, width, height)).convert("RGB").save(destination_path)
            frames.append((destination_path, elapsed))
    finally:
        chrome.request("Page.stopScreencast")
    if len(frames) < 30 or frames[-1][1] < 19:
        raise RuntimeError(
            f"Incomplete recording: {len(frames)} frames, {frames[-1][1]}s"
        )
    return frames


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--browser-endpoint-file", required=True, type=Path)
    parser.add_argument("--recording", type=Path)
    arguments = parser.parse_args()
    root = Path(__file__).resolve().parent
    frames_directory = root.parent / ".preview-frames"
    frames_directory.mkdir(exist_ok=True)
    endpoint = arguments.browser_endpoint_file.read_text().splitlines()
    reverse_html = MarkdownIt().render((root / "back.md").read_text())
    card_script = (root / "card.js").read_text()
    with connect(
        f"ws://127.0.0.1:{endpoint[0]}{endpoint[1]}",
        proxy=None,
        max_size=32 * 1024 * 1024,
    ) as connection:
        chrome = ChromeConnection(connection)
        targets = chrome.request("Target.getTargets")["targetInfos"]
        profile_targets = [
            target
            for target in targets
            if target["url"] == "https://github.com/Castrozan"
        ]
        if len(profile_targets) != 1:
            raise RuntimeError(
                "Open exactly one Castrozan profile tab in the connected Chrome instance"
            )
        session = chrome.request(
            "Target.attachToTarget",
            {"targetId": profile_targets[0]["targetId"], "flatten": True},
        )
        chrome.session_identifier = session["sessionId"]
        try:
            chrome.request("Page.bringToFront")
            chrome.evaluate(
                "(async () => { await document.fonts.ready; "
                "await Promise.all([...document.querySelectorAll('article.markdown-body img')]"
                ".map(image => image.decode())); return true; })()"
            )
            dimensions = chrome.evaluate(
                f"{card_script}\nmountProfileReadmeCard({json.dumps(reverse_html)})"
            )
            width, height = dimensions["width"], dimensions["height"]
            chrome.screenshot(frames_directory / "front.png", width, height)
            chrome.evaluate("window.profileReadmeCard.animation.currentTime = 11000")
            chrome.screenshot(frames_directory / "back.png", width, height)
            chrome.evaluate("window.profileReadmeCard.animation.currentTime = 0")
            frames = (
                read_recording(arguments.recording, frames_directory)
                if arguments.recording
                else record_frames(chrome, frames_directory, width, height)
            )
            frames = render_turns(chrome, frames, frames_directory, width, height)
        finally:
            chrome.evaluate("window.profileReadmeCard?.restore()")
    output = root / "readme-flip.gif"
    encode_recording(frames, output)
    print(
        json.dumps(
            {
                "output": str(output),
                "frames": len(frames),
                "width": width,
                "height": height,
                "bytes": output.stat().st_size,
            }
        )
    )


if __name__ == "__main__":
    main()
