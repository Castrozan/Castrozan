import argparse
from contextlib import contextmanager
import json
from pathlib import Path
import subprocess
import time

from browser import isolated_browser
from encode import encode_recording
from media import read_media
from render import render_frames
from timing import TIMING


def load_markdown(chrome, theme_script, theme, source_revision, face):
    url = (
        f"https://github.com/Castrozan/Castrozan/blob/{source_revision}"
        f"/preview/scene/{face}.md"
    )
    chrome.request("Page.navigate", {"url": url})
    deadline = time.monotonic() + 40
    required_element = "pre" if face == "front" else "h1"
    while not chrome.evaluate(
        f"location.pathname.endsWith('/{face}.md') && document.readyState !== 'loading'"
        f" && !!document.querySelector('article.markdown-body {required_element}')"
    ):
        if time.monotonic() > deadline:
            state = chrome.evaluate(
                "({url:location.href,title:document.title,ready:document.readyState,"
                "text:document.body.innerText.slice(0,300)})"
            )
            raise RuntimeError(f"Published Markdown did not load: {state}")
        time.sleep(0.1)
    background = chrome.evaluate(
        f"{theme_script}\napplyProfileTheme({json.dumps(theme)})"
    )
    expected = "rgb(255, 255, 255)" if theme == "light" else "rgb(13, 17, 23)"
    if background != expected:
        raise RuntimeError(f"Unexpected {theme} background: {background}")
    deadline = time.monotonic() + 5
    previous_bounds = None
    stable_measurements = 0
    while stable_measurements < 3:
        bounds = chrome.evaluate(
            "(() => {const bounds=document.querySelector('article.markdown-body').getBoundingClientRect();"
            "return {width:bounds.width,height:bounds.height};})()"
        )
        stable_measurements = (
            stable_measurements + 1
            if bounds == previous_bounds and bounds["width"] == 846
            else 0
        )
        previous_bounds = bounds
        if time.monotonic() > deadline:
            raise RuntimeError(f"GitHub Markdown layout did not settle: {bounds}")
        time.sleep(0.1)
    return chrome.evaluate(
        "(() => { const article=document.querySelector('article.markdown-body');"
        "const bounds=article.getBoundingClientRect();return {html:article.innerHTML,"
        "width:bounds.width,height:bounds.height}; })()"
    )


@contextmanager
def profile_preview(theme):
    root = Path(__file__).resolve().parent
    source_paths = [
        "preview/scene/front.md",
        "preview/scene/back.md",
        "preview/scene/assets",
    ]
    subprocess.run(
        ["git", "diff", "--quiet", "HEAD", "--", *source_paths],
        cwd=root.parent,
        check=True,
    )
    source_revision = subprocess.check_output(
        ["git", "log", "-1", "--format=%H", "--", *source_paths],
        cwd=root.parent,
        text=True,
    ).strip()
    card_script = (root / "scene" / "card.js").read_text()
    media_script = (root / "scene" / "media.js").read_text()
    theme_script = (root / "scene" / "theme.js").read_text()
    with isolated_browser(theme) as chrome:
        try:
            reverse_face = load_markdown(
                chrome, theme_script, theme, source_revision, "back"
            )
            load_markdown(chrome, theme_script, theme, source_revision, "front")
            dimensions = chrome.evaluate(
                f"{card_script}\nmountProfileReadmeCard("
                f"{json.dumps(reverse_face)}, {json.dumps(TIMING)})"
            )
            width, height = dimensions["width"], dimensions["height"]
            sources = chrome.evaluate(
                "[...document.querySelectorAll('[data-readme-face] article.markdown-body img')]"
                ".filter(image => image.getBoundingClientRect().width && "
                "/\\.(gif|svg)$/.test(new URL(image.currentSrc).pathname))"
                ".map(image => image.currentSrc)"
            )
            assets = read_media(sources)
            chrome.evaluate(
                f"{media_script}\nmountProfileReadmeMedia({json.dumps(assets)})"
            )
            chrome.evaluate(
                "document.documentElement.style.setProperty('background-color',"
                "'transparent','important');document.body.style.setProperty("
                "'background-color','transparent','important')"
            )
            chrome.request(
                "Emulation.setDefaultBackgroundColorOverride",
                {"color": {"r": 0, "g": 0, "b": 0, "a": 0}},
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
