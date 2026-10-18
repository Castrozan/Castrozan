import json
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from build import inspect_gif

source = Path(sys.argv[1]).resolve()
root = Path(__file__).resolve().parent
metadata = inspect_gif(source.read_bytes())
hold_index, (_, old_delay) = max(
    enumerate(metadata["controls"]), key=lambda item: item[1][1]
)
remaining_ticks = 360000 - round(metadata["seconds"] * 100) + old_delay
command = [
    "gifsicle",
    "--merge",
    "--conserve-memory",
    str(source),
    f"#0-{hold_index - 1}",
]
while remaining_ticks > 0:
    delay = min(65535, remaining_ticks)
    command.extend(["--delay", str(delay), str(source), f"#{hold_index}"])
    remaining_ticks -= delay
output = root / "native-hour.gif"
command.extend(
    ["--same-delay", str(source), f"#{hold_index + 1}-", "--output", str(output)]
)
subprocess.run(command, check=True)
metadata = inspect_gif(output.read_bytes())
assert metadata["seconds"] == 3600, metadata["seconds"]
measurements = {
    "bytes": output.stat().st_size,
    "seconds": metadata["seconds"],
    "frames": metadata["frames"],
    "turns": 2,
    "source_hold_frame": hold_index,
}
(root / "measurements.json").write_text(json.dumps(measurements, indent=2) + "\n")
(root / "README.md").write_text(f"""# One-hour native Markdown GIF stress fixture

This extends only the static reverse-face reading interval of the native Markdown recording. It tests encoded duration without adding turns or pretending the page was recorded continuously for an hour.

{measurements["bytes"]:,} bytes, 3,600 seconds, two turns and {measurements["frames"]} frames. Each individual frame delay stays within GIF89a's 16-bit delay field.

![One-hour duration stress fixture](native-hour.gif)
""")
print(json.dumps(measurements, indent=2), flush=True)
