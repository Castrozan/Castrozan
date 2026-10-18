import json
from pathlib import Path

TIMING = json.loads((Path(__file__).parent / "scene" / "timing.json").read_text())
