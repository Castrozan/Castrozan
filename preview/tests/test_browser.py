import base64
import io
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from PIL import Image

from browser import isolated_browser
from media import decode_gif
from record import profile_preview


@unittest.skipUnless(
    os.environ.get("PROFILE_BROWSER_TESTS"), "Isolated browser tests disabled"
)
class BrowserMediaTests(unittest.TestCase):
    def test_reverse_face_gif_uses_the_shared_seekable_clock(self):
        frames = [Image.new("RGB", (2, 2), color) for color in ["red", "blue"]]
        buffer = io.BytesIO()
        frames[0].save(
            buffer,
            format="GIF",
            save_all=True,
            append_images=frames[1:],
            duration=100,
            loop=0,
        )
        source = "data:image/gif;base64," + base64.b64encode(buffer.getvalue()).decode()
        asset = {"source": source, **decode_gif(buffer.getvalue())}
        fixture = (
            '<div data-readme-face="front"><article class="markdown-body">'
            "Front face</article></div>"
            '<div data-readme-face="back"><article class="markdown-body">'
            f'<img src="{source}"></article></div>'
        )
        script = (
            Path(__file__).resolve().parents[1] / "scene" / "media.js"
        ).read_text()
        with isolated_browser("dark") as chrome:
            chrome.evaluate(f"document.body.innerHTML = {json.dumps(fixture)}")
            chrome.evaluate("document.querySelector('img').decode()")
            chrome.evaluate(f"{script}\nmountProfileReadmeMedia({json.dumps([asset])})")
            for milliseconds, frame_number in [(0, 0), (100, 1), (200, 0)]:
                with self.subTest(milliseconds=milliseconds):
                    chrome.evaluate(f"window.profileReadmeMedia.seek({milliseconds})")
                    self.assertEqual(
                        chrome.evaluate("document.querySelector('img').src"),
                        asset["frames"][frame_number]["source"],
                    )
            chrome.evaluate("window.profileReadmeMedia.restore()")
            self.assertEqual(
                chrome.evaluate("document.querySelector('img').src"), source
            )

    def test_embedded_media_advances_at_a_fixed_card_pose_during_both_turns(self):
        for theme in ["light", "dark"]:
            with (
                self.subTest(theme=theme),
                TemporaryDirectory() as directory,
                profile_preview(theme) as (chrome, width, height),
            ):
                self.assertEqual(
                    chrome.evaluate("getComputedStyle(document.body).backgroundColor"),
                    "rgba(0, 0, 0, 0)",
                )
                self.assertEqual(
                    chrome.evaluate("document.documentElement.dataset.colorMode"),
                    theme,
                )
                self.assertEqual(chrome.evaluate("document.body.childElementCount"), 1)
                self.assertEqual(
                    chrome.evaluate(
                        "['article.markdown-body','article.markdown-body table tr',"
                        "'article.markdown-body pre'].map(selector=>"
                        "getComputedStyle(document.querySelector(selector)).backgroundColor)"
                    ),
                    ["rgba(0, 0, 0, 0)"] * 3,
                )
                self.assertEqual(width, 846)
                self.assertLessEqual(height, 1100)
                self.assertIn(
                    f"nix-{theme}.gif",
                    chrome.evaluate(
                        "document.querySelector('article.markdown-body img[src^=\"data:image/png;base64,\"]').closest('a').href"
                    ),
                )
                snake_color = chrome.evaluate(
                    "getComputedStyle([...document.querySelectorAll('article.markdown-body span')].find(el=>el.shadowRoot).shadowRoot.querySelector('.s')).fill"
                )
                self.assertEqual(
                    snake_color,
                    "rgb(9, 105, 218)" if theme == "light" else "rgb(121, 192, 255)",
                )
                layout = chrome.evaluate(
                    "(() => {const reverse=document.querySelector('[data-readme-face=back] article');"
                    "const front=document.querySelector('[data-readme-face=front] article');"
                    "return {reverseHeight:reverse.scrollHeight,"
                    "languageText:front.querySelector('pre').textContent,"
                    "lambdaWidth:front.querySelector('img[src^=\"data:image/png\"]').width,"
                    "headingSize:getComputedStyle(reverse.querySelector('h1')).fontSize,"
                    "source:location.pathname};})()"
                )
                self.assertLessEqual(layout["reverseHeight"], height)
                self.assertIn("Python", layout["languageText"])
                self.assertIn("▓", layout["languageText"])
                self.assertEqual(layout["lambdaWidth"], 200)
                self.assertEqual(layout["headingSize"], "32px")
                self.assertTrue(layout["source"].endswith("/preview/scene/front.md"))
                crops = chrome.evaluate(
                    "(() => { const article = document.querySelector('article.markdown-body'); "
                    "const image = article.querySelector('img[src^=\"data:image/png;base64,\"]'); "
                    "const vector = [...article.querySelectorAll('span')]"
                    ".find(element => element.shadowRoot).shadowRoot.querySelector('svg'); "
                    "return Object.fromEntries(Object.entries({nix: image, snake: vector})"
                    ".map(([name, element]) => { const bounds = element.getBoundingClientRect(); "
                    "return [name, [bounds.left, bounds.top, bounds.right, bounds.bottom]]; })); })()"
                )

                def capture(milliseconds):
                    chrome.evaluate(f"window.profileReadmeMedia.seek({milliseconds})")
                    destination = Path(directory) / f"media-{milliseconds}.png"
                    chrome.screenshot(destination, width, height)
                    with Image.open(destination) as image:
                        image = image.convert("RGBA")
                        if milliseconds == 11300:
                            self.assertEqual(
                                image.getpixel((width - 1, height - 1))[3], 0
                            )
                            self.assertEqual(image.getchannel("A").getextrema()[1], 255)
                        if milliseconds == 0:
                            self.assertEqual(image.getpixel((10, 10))[3], 0)
                        return {
                            name: image.crop(bounds).tobytes()
                            for name, bounds in crops.items()
                        }

                for start, end in [(11300, 11800), (23300, 23800)]:
                    before = capture(start)
                    after = capture(end)
                    for name in crops:
                        with self.subTest(turn=start, media=name):
                            self.assertNotEqual(before[name], after[name])
                    self.assertEqual(before, capture(start))
                self.assertEqual(capture(0)["nix"], capture(2400)["nix"])
                snake_duration = chrome.evaluate(
                    "[...document.querySelectorAll('article.markdown-body span')].find(element=>element.shadowRoot).shadowRoot.querySelector('svg').getAttribute('data-animation-duration')"
                )
                self.assertEqual(
                    capture(0)["snake"], capture(int(snake_duration))["snake"]
                )
                chrome.evaluate(
                    "window.profileReadmeCard.animation.currentTime = 16000"
                )
                crops = chrome.evaluate(
                    "(() => {const article=document.querySelector('[data-readme-face=back] article');"
                    "const image=article.querySelector('img[src^=\"data:image/png;base64,\"]');"
                    "const vector=[...article.querySelectorAll('span')]"
                    ".find(element=>element.shadowRoot).shadowRoot.querySelector('svg');"
                    "return Object.fromEntries(Object.entries({ambient:image,map:vector})"
                    ".map(([name,element])=>{const bounds=element.getBoundingClientRect();"
                    "return [name,[bounds.left,bounds.top,bounds.right,bounds.bottom]];}));})()"
                )
                for start, end in [(13000, 13500), (18000, 18500), (22200, 22700)]:
                    before = capture(start)
                    after = capture(end)
                    for name in crops:
                        with self.subTest(reverse=start, media=name):
                            self.assertNotEqual(before[name], after[name])
                    self.assertEqual(before, capture(start))
                self.assertEqual(capture(0)["ambient"], capture(8000)["ambient"])


if __name__ == "__main__":
    unittest.main()
