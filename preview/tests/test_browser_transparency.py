import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from PIL import Image

from record import profile_preview


@unittest.skipUnless(
    os.environ.get("PROFILE_BROWSER_TESTS"), "Isolated browser tests disabled"
)
class BrowserTransparencyTests(unittest.TestCase):
    def test_markdown_surfaces_reveal_custom_backgrounds_in_both_themes(self):
        background_colors = [
            (232, 221, 245, 255),
            (32, 55, 44, 255),
        ]
        for theme in ["light", "dark"]:
            with (
                self.subTest(theme=theme),
                TemporaryDirectory() as directory,
                profile_preview(theme) as (chrome, width, height),
            ):
                surfaces = chrome.evaluate(
                    "['article.markdown-body','article.markdown-body table tr',"
                    "'article.markdown-body pre'].map(selector=>"
                    "getComputedStyle(document.querySelector(selector)).backgroundColor)"
                )
                self.assertEqual(surfaces, ["rgba(0, 0, 0, 0)"] * 3)
                self.assertEqual(chrome.evaluate("document.body.childElementCount"), 1)
                chrome.evaluate(
                    "window.profileReadmeMedia.seek(0);"
                    "window.profileReadmeCard.animation.currentTime = 0"
                )
                destination = Path(directory) / "transparent-canvas.png"
                chrome.screenshot(destination, width, height)
                with Image.open(destination) as screenshot:
                    frame = screenshot.convert("RGBA")
                    transparent_pixel = frame.getpixel((10, 10))
                    self.assertEqual(transparent_pixel[3], 0)
                    self.assertEqual(frame.getpixel((width - 1, height - 1))[3], 0)
                    self.assertEqual(frame.getchannel("A").getextrema()[1], 255)
                    for background_color in background_colors:
                        background = Image.new("RGBA", frame.size, background_color)
                        background.alpha_composite(frame)
                        self.assertEqual(
                            background.getpixel((10, 10)), background_color
                        )


if __name__ == "__main__":
    unittest.main()
