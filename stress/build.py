import json
from pathlib import Path
import struct
import subprocess


def inspect_gif(data):
    cursor = 13
    if data[10] & 128:
        cursor += 3 * (2 ** ((data[10] & 7) + 1))
    durations = []
    delay = 0
    controls = []
    while data[cursor] != 59:
        marker = data[cursor]
        cursor += 1
        if marker == 33:
            extension = data[cursor]
            cursor += 1
            if extension == 249:
                delay = struct.unpack_from("<H", data, cursor + 2)[0]
                controls.append((cursor + 2, delay))
        elif marker == 44:
            packed = data[cursor + 8]
            cursor += 9
            if packed & 128:
                cursor += 3 * (2 ** ((packed & 7) + 1))
            cursor += 1
            durations.append(delay)
            delay = 0
        else:
            raise ValueError(f"Unexpected GIF marker: {marker}")
        while data[cursor]:
            cursor += data[cursor] + 1
        cursor += 1
    return {
        "frames": len(durations),
        "seconds": sum(durations) / 100,
        "controls": controls,
    }


def main():
    root = Path(__file__).resolve().parent
    source = root.parent / "preview/readme-flip-dark.gif"
    cases = []
    for cycles in [3, 7, 15]:
        output = root / f"{cycles}-cycles.gif"
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
        metadata = inspect_gif(output.read_bytes())
        cases.append(
            {
                "name": f"{cycles}-cycles",
                "bytes": output.stat().st_size,
                "frames": metadata["frames"],
                "seconds": metadata["seconds"],
                "turns": cycles * 2,
            }
        )
    extended = bytearray(source.read_bytes())
    offset, delay = max(
        inspect_gif(extended)["controls"], key=lambda control: control[1]
    )
    struct.pack_into("<H", extended, offset, 65535)
    (root / "long-hold.gif").write_bytes(extended)
    metadata = inspect_gif(extended)
    cases.append(
        {
            "name": "long-hold",
            "bytes": len(extended),
            "frames": metadata["frames"],
            "seconds": metadata["seconds"],
            "turns": 2,
        }
    )
    for case in cases:
        if case["bytes"] > 100 * 1024 * 1024:
            raise ValueError(f"{case['name']} exceeds GitHub ordinary Git file limit")
        directory = root / case["name"]
        directory.mkdir(exist_ok=True)
        (directory / "README.md").write_text(
            f"# GIF stress test: {case['name']}\n\n{case['bytes']:,} bytes, {case['seconds']} seconds, {case['turns']} turns, {case['frames']} frames.\n\n![Recorded README stress fixture](../{case['name']}.gif)\n"
        )
    (root / "measurements.json").write_text(json.dumps(cases, indent=2) + "\n")
    (root / "README.md").write_text(
        "# README GIF stress tests\n\nThese fixtures repeat the existing recording to measure real GIF bytes, turns and duration. The long-hold fixture extends only the static reverse-face reading interval. They are benchmarks, not the revised profile design.\n\n"
        + "\n".join(
            f"- [{case['name']}]({case['name']}/README.md): {case['bytes']:,} bytes, {case['seconds']} seconds, {case['turns']} turns."
            for case in cases
        )
        + "\n"
    )
    print(json.dumps(cases, indent=2), flush=True)


if __name__ == "__main__":
    main()
