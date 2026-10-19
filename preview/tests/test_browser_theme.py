import json
import os
from pathlib import Path
import unittest

from markdown_it import MarkdownIt

from browser import isolated_browser


@unittest.skipUnless(
    os.environ.get("PROFILE_BROWSER_TESTS"), "Isolated browser tests disabled"
)
class BrowserThemeTests(unittest.TestCase):
    def test_github_theme_selects_image_when_system_theme_disagrees(self):
        root = Path(__file__).resolve().parents[1]
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
