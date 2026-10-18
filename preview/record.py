import argparse
from contextlib import contextmanager
import json
from pathlib import Path

from markdown_it import MarkdownIt

from browser import isolated_browser
from encode import encode_recording
from media import read_media
from render import render_frames


@contextmanager
def profile_preview(theme):
    root = Path(__file__).resolve().parent
    reverse_html = MarkdownIt().render((root / "back.md").read_text())
    card_script = (root / "scene" / "card.js").read_text()
    media_script = (root / "scene" / "media.js").read_text()
    theme_script = (root / "scene" / "theme.js").read_text()
    with isolated_browser(theme) as chrome:
        try:
            background = chrome.evaluate(
                f"{theme_script}\napplyProfileTheme({json.dumps(theme)})"
            )
            expected_background = (
                "rgb(255, 255, 255)" if theme == "light" else "rgb(13, 17, 23)"
            )
            if background != expected_background:
                raise RuntimeError(f"Unexpected {theme} background: {background}")
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
                f"{media_script}\nmountProfileReadmeMedia("
                f"applyProfileMediaTheme({json.dumps(assets)}, {json.dumps(theme)}))"
            )
            yield chrome, width, height
        finally:
            chrome.evaluate("window.profileReadmeMedia?.restore()")
            chrome.evaluate("window.profileReadmeCard?.restore()")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--theme", required=True, choices=["light", "dark"])
    arguments = parser.parse_args()
    root = Path(__file__).resolve().parent
    frames_directory = root.parent / ".preview-frames" / arguments.theme
    frames_directory.mkdir(parents=True, exist_ok=True)
    with profile_preview(arguments.theme) as (chrome, width, height):
        frames = render_frames(chrome, frames_directory, width, height)
    output = root / f"readme-flip-{arguments.theme}.gif"
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
