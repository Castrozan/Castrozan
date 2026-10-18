import base64
import io
from pathlib import Path
import subprocess
from urllib.request import urlopen

from PIL import Image

from browser import isolated_browser

AMBIENT_REVISION = "8197b0849d313222726bb421e0db5b2411036b60"
AMBIENT_SOURCE = (
    f"https://raw.githubusercontent.com/Castrozan/.dotfiles/{AMBIENT_REVISION}/"
    "machine-configuration/desktop/appearance/screensaver/ambient-canvas/web/"
)
AMBIENT_SCRIPTS = [
    "ambient_canvas_palette.js",
    "scenes/ascii-invader/ascii_invader_shell.js",
    "scenes/ascii-invader/ascii_invader_glyph_field.js",
    "scenes/ascii-invader/ascii_invader_crt_shaders.js",
    "scenes/ascii-invader/ascii_invader_scene.js",
    "scenes/ascii-plotter/ascii_plotter_traces.js",
    "scenes/ascii-plotter/ascii_plotter_schematic.js",
    "scenes/ascii-plotter/ascii_plotter_scene.js",
]


def record_ambient_canvas(destination):
    scripts = []
    for source in AMBIENT_SCRIPTS:
        with urlopen(AMBIENT_SOURCE + source, timeout=30) as response:
            scripts.append(response.read().decode())
    frames = []
    with isolated_browser("dark") as chrome:
        for script in scripts:
            chrome.evaluate(script)
        chrome.evaluate(
            """(() => {
              const output = document.createElement('canvas');
              output.width = 846;
              output.height = 228;
              const invader = document.createElement('canvas');
              invader.width = 300;
              invader.height = 228;
              const plotter = document.createElement('canvas');
              plotter.width = 544;
              plotter.height = 228;
              const factories = window.AMBIENT_CANVAS_SCENE_FACTORIES;
              const left = factories['ascii-invader'](invader, {preserveDrawingBuffer:true});
              const right = factories['ascii-plotter'](plotter);
              const context = output.getContext('2d');
              window.renderAmbientPreview = seconds => {
                left.render(seconds);
                right.render(seconds);
                context.fillStyle = window.AmbientCanvasPalette.backgroundHex;
                context.fillRect(0, 0, output.width, output.height);
                context.drawImage(invader, 0, 0);
                context.drawImage(plotter, 302, 0);
                return output.toDataURL('image/png');
              };
            })()"""
        )
        for frame_number in range(160):
            source = chrome.evaluate(
                f"window.renderAmbientPreview({frame_number / 20})"
            )
            with Image.open(
                io.BytesIO(base64.b64decode(source.split(",")[1]))
            ) as frame:
                frames.append(
                    frame.quantize(colors=96, method=Image.Quantize.FASTOCTREE)
                )
    frames[0].save(
        destination,
        save_all=True,
        append_images=frames[1:],
        duration=50,
        loop=0,
        optimize=True,
    )
    subprocess.run(
        ["gifsicle", "--batch", "--optimize=3", str(destination)], check=True
    )
    print(f"{destination.name}: {destination.stat().st_size:,} bytes", flush=True)


def write_system_graph(destination, theme):
    foreground, background, border, accent = (
        ("#24292f", "#f6f8fa", "#8c959f", "#0969da")
        if theme == "light"
        else ("#e6edf3", "#161b22", "#6e7681", "#58a6ff")
    )
    connections = [
        "M132 85H177V40H227",
        "M132 85H177V130H227",
        "M362 40H402V85H437",
        "M362 130H402V85H437",
        "M597 85H631V40H662",
        "M597 85H631V130H662",
    ]
    nodes = [
        (2, 65, 130, "Nix flake"),
        (227, 20, 135, "NixOS"),
        (227, 110, 135, "nix-darwin"),
        (437, 65, 160, "Home Manager"),
        (662, 20, 182, "Desktop + tools"),
        (662, 110, 182, "Agent harnesses"),
    ]
    elements = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="846" height="170" viewBox="0 0 846 170" role="img" aria-label="A Nix flake builds NixOS and nix-darwin. Home Manager supplies desktop tools and agent harnesses on both." data-animation-duration="4000">',
        "<style>@keyframes signal{to{stroke-dashoffset:-240}}.signal{stroke-dasharray:6 54;animation:signal 4s linear infinite}</style>",
        f'<g fill="none" stroke="{border}" stroke-width="2">',
        *(f'<path d="{connection}"/>' for connection in connections),
        "</g>",
        f'<g fill="none" stroke="{accent}" stroke-width="3">',
        *(f'<path class="signal" d="{connection}"/>' for connection in connections),
        "</g>",
    ]
    for left, top, width, label in nodes:
        elements.extend(
            [
                f'<rect x="{left}" y="{top}" width="{width}" height="40" rx="5" fill="{background}" stroke="{border}"/>',
                f'<text x="{left + width / 2}" y="{top + 25}" text-anchor="middle" fill="{foreground}" font-family="monospace" font-size="15">{label}</text>',
            ]
        )
    elements.append("</svg>")
    destination.write_text("\n".join(elements) + "\n")


def main():
    destination = Path(__file__).parent / "scene" / "assets"
    record_ambient_canvas(destination / "ambient-canvas.gif")
    for theme in ["light", "dark"]:
        write_system_graph(destination / f"system-map-{theme}.svg", theme)


if __name__ == "__main__":
    main()
