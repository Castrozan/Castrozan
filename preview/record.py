import argparse
from contextlib import contextmanager
import json
from pathlib import Path

from markdown_it import MarkdownIt
from websockets.sync.client import connect

from chrome import ChromeConnection
from encode import encode_recording
from media import read_media
from render import render_frames


@contextmanager
def profile_preview(endpoint_file):
    root = Path(__file__).resolve().parent
    endpoint = endpoint_file.read_text().splitlines()
    reverse_html = MarkdownIt().render((root / "back.md").read_text())
    card_script = (root / "card.js").read_text()
    media_script = (root / "media.js").read_text()
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
            sources = chrome.evaluate(
                "[...document.querySelectorAll('article.markdown-body img')]"
                ".filter(image => image.getBoundingClientRect().width && "
                "/\\.(gif|svg)$/.test(new URL(image.currentSrc).pathname))"
                ".map(image => image.currentSrc)"
            )
            assets = read_media(sources)
            dimensions = chrome.evaluate(
                f"{card_script}\nmountProfileReadmeCard({json.dumps(reverse_html)})"
            )
            width, height = dimensions["width"], dimensions["height"]
            chrome.evaluate(
                f"{media_script}\nmountProfileReadmeMedia({json.dumps(assets)})"
            )
            yield chrome, width, height
        finally:
            chrome.evaluate("window.profileReadmeMedia?.restore()")
            chrome.evaluate("window.profileReadmeCard?.restore()")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--browser-endpoint-file", required=True, type=Path)
    arguments = parser.parse_args()
    root = Path(__file__).resolve().parent
    frames_directory = root.parent / ".preview-frames"
    frames_directory.mkdir(exist_ok=True)
    with profile_preview(arguments.browser_endpoint_file) as (chrome, width, height):
        frames = render_frames(chrome, frames_directory, width, height)
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
