from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from PIL import Image, ImageChops, ImageDraw, ImageStat

from encode import encode_recording

STATIC_COLOR_TOLERANCE = 12
STATIC_DRIFT_TOLERANCE = 8
STATIC_REGION_CLEAR_OF_ANIMATED_BLOCKS = (0, 0, 56, 64)


class EncodeTests(unittest.TestCase):
    def test_static_content_stays_stable_while_neighbors_animate(self):
        static_colors = [
            (block * 37 % 256, block * 91 % 256, block * 19 % 256) for block in range(8)
        ]
        with TemporaryDirectory() as directory:
            destination = Path(directory)
            frames = []
            for index, animated_color in enumerate(
                [(255, 0, 255), (0, 0, 255), (0, 255, 255)]
            ):
                frame = Image.new("RGB", (128, 64), animated_color)
                draw = ImageDraw.Draw(frame)
                for block, color in enumerate(static_colors):
                    draw.rectangle((block * 8, 0, block * 8 + 7, 63), fill=color)
                path = destination / f"frame-{index}.png"
                frame.save(path)
                frames.append((path, index * 8))
            expected = frame.crop(STATIC_REGION_CLEAR_OF_ANIMATED_BLOCKS)
            output = destination / "recording.avif"
            encode_recording(frames, output)
            with Image.open(output) as animation:
                first = animation.convert("RGB").crop(
                    STATIC_REGION_CLEAR_OF_ANIMATED_BLOCKS
                )
                self.assertTrue(
                    all(
                        channel_mean <= STATIC_COLOR_TOLERANCE
                        for channel_mean in ImageStat.Stat(
                            ImageChops.difference(first, expected)
                        ).mean
                    )
                )
                for number in range(animation.n_frames):
                    animation.seek(number)
                    actual = animation.convert("RGB").crop(
                        STATIC_REGION_CLEAR_OF_ANIMATED_BLOCKS
                    )
                    self.assertLessEqual(
                        max(
                            channel_maximum
                            for _, channel_maximum in ImageChops.difference(
                                actual, first
                            ).getextrema()
                        ),
                        STATIC_DRIFT_TOLERANCE,
                    )

    def test_transparent_canvas_survives_avif_encoding(self):
        colors = ["red", "blue", "green"]
        with TemporaryDirectory() as directory:
            destination = Path(directory)
            frames = []
            for index, color in enumerate(colors):
                frame = Image.new("RGBA", (128, 64), (0, 0, 0, 0))
                ImageDraw.Draw(frame).rectangle((16, 16, 48, 48), fill=color)
                path = destination / f"frame-{index}.png"
                frame.save(path)
                frames.append((path, index * 8))
            output = destination / "recording.avif"
            encode_recording(frames, output)
            with Image.open(output) as animation:
                for index, color in enumerate(colors):
                    animation.seek(index * 400)
                    frame = animation.convert("RGBA")
                    self.assertEqual(frame.getpixel((0, 0))[3], 0)
                    expected = Image.new("RGB", (1, 1), color).getpixel((0, 0))
                    actual = frame.getpixel((32, 32))
                    self.assertEqual(actual[3], 255)
                    for actual_channel, expected_channel in zip(actual, expected):
                        self.assertLessEqual(
                            abs(actual_channel - expected_channel),
                            STATIC_COLOR_TOLERANCE,
                        )


if __name__ == "__main__":
    unittest.main()
