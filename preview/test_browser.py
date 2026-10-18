import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from PIL import Image

from record import profile_preview


@unittest.skipUnless(
    os.environ.get("PROFILE_BROWSER_ENDPOINT_FILE"), "Chrome endpoint required"
)
class BrowserMediaTests(unittest.TestCase):
    def test_embedded_media_advances_at_a_fixed_card_pose_during_both_turns(self):
        endpoint = Path(os.environ["PROFILE_BROWSER_ENDPOINT_FILE"])
        with TemporaryDirectory() as directory:
            with profile_preview(endpoint) as (chrome, width, height):
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


if __name__ == "__main__":
    unittest.main()
