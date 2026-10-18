import hashlib
import json
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from build import inspect_gif

source = Path(sys.argv[1]).resolve()
root = Path(__file__).resolve().parent
source_metadata = inspect_gif(source.read_bytes())
cycles = (100 * 1024 * 1024) // source.stat().st_size
output = root / "native-max.gif"
while cycles > 0:
    subprocess.run(
        [
            "gifsicle",
            "--merge",
            "--conserve-memory",
            *([str(source)] * cycles),
            "--output",
            str(output),
        ],
        check=True,
    )
    if output.stat().st_size <= 100 * 1024 * 1024:
        break
    cycles -= 1
if cycles == 0:
    raise ValueError("The native recording exceeds the ordinary Git file limit")
metadata = inspect_gif(output.read_bytes())
measurements = {
    "bytes": output.stat().st_size,
    "seconds": metadata["seconds"],
    "frames": metadata["frames"],
    "turns": cycles * 2,
    "complete_cycles": cycles,
    "source_bytes": source.stat().st_size,
    "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
    "source_seconds": source_metadata["seconds"],
}
(root / "measurements.json").write_text(json.dumps(measurements, indent=2) + "\n")
(root / "README.md").write_text(f"""# Native Markdown recording stress test

This repeats the new recording of GitHub-rendered Markdown, preserving the original language bars, 200-pixel lambda, calendar labels and slower snake.

{measurements["bytes"]:,} bytes, {measurements["seconds"]} seconds, {measurements["turns"]} turns and {measurements["frames"]} frames. This is {cycles} complete copies of the {source_metadata["seconds"]}-second native recording below GitHub's 100 MiB ordinary Git file limit.

![Native Markdown recording stress fixture](native-max.gif)
""")
print(json.dumps(measurements, indent=2), flush=True)
