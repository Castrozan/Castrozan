import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from markdown_it import MarkdownIt
from PIL import Image

from browser import isolated_browser
from record import profile_preview


@unittest.skipUnless(
    os.environ.get("PROFILE_BROWSER_TESTS"), "Isolated browser tests disabled"
)
class BrowserMediaTests(unittest.TestCase):
    def test_embedded_media_advances_at_a_fixed_card_pose_during_both_turns(self):
        for theme in ["light", "dark"]:
            with (
                self.subTest(theme=theme),
                TemporaryDirectory() as directory,
                profile_preview(theme) as (chrome, width, height),
            ):
                expected = (
                    "rgb(255, 255, 255)" if theme == "light" else "rgb(13, 17, 23)"
                )
                self.assertEqual(
                    chrome.evaluate("getComputedStyle(document.body).backgroundColor"),
                    expected,
                )
                self.assertEqual((width, height), (846, 819))
                self.assertIn(
                    f"nix-{theme}.gif",
                    chrome.evaluate(
                        "document.querySelector('article.markdown-body img[src^=\"data:image/png;base64,\"]').closest('a').href"
                    ),
                )
                vector_background = chrome.evaluate(
                    "[...document.querySelectorAll('article.markdown-body span')].find(el=>el.shadowRoot).shadowRoot.querySelector('rect').getAttribute('fill')"
                )
                self.assertEqual(
                    vector_background, "#fff" if theme == "light" else "#0d1117"
                )
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
                        return {
                            name: image.crop(bounds).tobytes()
                            for name, bounds in crops.items()
                        }

                for start, end in [(9200, 9700), (19400, 19900)]:
                    before = capture(start)
                    after = capture(end)
                    for name in crops:
                        with self.subTest(turn=start, media=name):
                            self.assertNotEqual(before[name], after[name])
                    self.assertEqual(before, capture(start))
                self.assertEqual(capture(0)["nix"], capture(2400)["nix"])

    def test_github_theme_selects_image_when_system_theme_disagrees(self):
        root = Path(__file__).resolve().parent
        html = MarkdownIt().render((root / "README.md").read_text())
        with isolated_browser("dark") as chrome:
            chrome.evaluate(
                f"document.querySelector('article.markdown-body').innerHTML = {json.dumps(html)}"
            )
            chrome.evaluate(
                "document.querySelectorAll('article.markdown-body img').forEach(image => {"
                "image.width = 2; image.height = 2; });"
            )
            for theme, system in [("light", "dark"), ("dark", "light")]:
                with self.subTest(github=theme, system=system):
                    chrome.request(
                        "Emulation.setEmulatedMedia",
                        {
                            "features": [
                                {"name": "prefers-color-scheme", "value": system}
                            ]
                        },
                    )
                    chrome.evaluate(
                        f"document.documentElement.dataset.colorMode = {json.dumps(theme)};"
                        "document.documentElement.dataset.lightTheme = 'light';"
                        "document.documentElement.dataset.darkTheme = 'dark';"
                    )
                    visible = chrome.evaluate(
                        "[...document.querySelectorAll('article.markdown-body img')]"
                        ".filter(image => image.getBoundingClientRect().width)"
                        ".map(image => image.getAttribute('src'))"
                    )
                    self.assertEqual(len(visible), 1)
                    self.assertIn(f"readme-flip-{theme}.gif", visible[0])


if __name__ == "__main__":
    unittest.main()
