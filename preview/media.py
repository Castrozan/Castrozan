import base64
import io
from urllib.parse import urlsplit
from urllib.request import urlopen

from PIL import Image


def decode_gif(data):
    frames = []
    elapsed = 0
    with Image.open(io.BytesIO(data)) as animation:
        for frame_number in range(animation.n_frames):
            animation.seek(frame_number)
            elapsed += animation.info["duration"]
            image = animation.convert("RGBA")
            image.info.clear()
            buffer = io.BytesIO()
            image.save(buffer, format="PNG")
            frames.append(
                {
                    "end": elapsed,
                    "source": "data:image/png;base64,"
                    + base64.b64encode(buffer.getvalue()).decode(),
                }
            )
    return {"frames": frames, "duration": elapsed}


def read_media(sources):
    assets = []
    for source in sources:
        with urlopen(source, timeout=30) as response:
            data = response.read()
        media = (
            decode_gif(data)
            if urlsplit(source).path.endswith(".gif")
            else {"svg": data.decode()}
        )
        assets.append({"source": source, **media})
    return assets
