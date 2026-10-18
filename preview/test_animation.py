import base64
import hashlib
import io
from pathlib import Path
import unittest

from PIL import Image

from media import decode_gif


class AnimationTests(unittest.TestCase):
    def test_embedded_gif_preserves_frames_and_durations(self):
        images = [Image.new("RGB", (2, 2), color) for color in ["red", "green", "blue"]]
        source = io.BytesIO()
        images[0].save(
            source,
            format="GIF",
            save_all=True,
            append_images=images[1:],
            duration=[40, 70, 110],
            loop=0,
        )
        animation = decode_gif(source.getvalue())
        self.assertEqual(animation["duration"], 220)
        self.assertEqual(
            [frame["end"] for frame in animation["frames"]], [40, 110, 220]
        )
        for expected, frame in zip(images, animation["frames"]):
            with Image.open(
                io.BytesIO(base64.b64decode(frame["source"].split(",")[1]))
            ) as actual:
                self.assertEqual(actual.convert("RGB").tobytes(), expected.tobytes())

    def test_both_turns_animate_at_fifty_frames_per_second(self):
        path = Path(__file__).with_name("readme-flip.gif")
        self.assertLessEqual(path.stat().st_size, 10_000_000)
        intervals = [(9500, 10500), (18700, 19700)]
        samples = {interval: [] for interval in intervals}
        elapsed = 0
        with Image.open(path) as animation:
            for frame_number in range(animation.n_frames):
                animation.seek(frame_number)
                duration = animation.info["duration"]
                for interval, frames in samples.items():
                    if interval[0] <= elapsed < interval[1]:
                        digest = hashlib.sha256(
                            animation.convert("RGB").tobytes()
                        ).digest()
                        frames.append((duration, digest))
                elapsed += duration
        self.assertEqual(elapsed, 20000)
        for interval, frames in samples.items():
            with self.subTest(interval=interval):
                self.assertEqual(len(frames), 50)
                self.assertTrue(all(duration == 20 for duration, _ in frames))
                self.assertGreaterEqual(len({digest for _, digest in frames}), 48)


if __name__ == "__main__":
    unittest.main()
