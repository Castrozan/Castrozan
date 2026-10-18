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


def write_site_architecture(destination):
    connections = [
        ("M210 35H324", "#FFD600"),
        ("M522 35H636", "#FFD600"),
        ("M112 58V83H423V112", "#FF6B35"),
        ("M210 135H324", "#FFD600"),
        ("M522 135H579V35H636", "#FFD600"),
        ("M522 135H636", "#FF6B35"),
        ("M735 112V58", "#FF6B35"),
    ]
    nodes = [
        (12, 12, "GitHub Actions", "build + deploy", "#FFD600"),
        (324, 12, "Artifact Registry", "container images", "#FFD600"),
        (636, 12, "Cloud Run apps", "health-gated rollouts", "#FFD600"),
        (12, 112, "lucaszanoni.com", "browser requests", "#FFD600"),
        (324, 112, "Cloudflare Worker", "edge routing", "#FFD600"),
        (636, 112, "Cloudflare Access", "private routes", "#FF6B35"),
    ]
    elements = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="846" height="174" viewBox="0 0 846 174" role="img" aria-label="GitHub Actions builds images for Artifact Registry and deploys Cloud Run apps. Terraform configures the edge. Browser requests pass through a Cloudflare Worker, with Access protecting private routes." data-animation-duration="4000">',
        "<style>@keyframes signal{to{stroke-dashoffset:-240}}.signal{stroke-dasharray:6 54;animation:signal 4s linear infinite}</style>",
        '<rect width="846" height="174" fill="#0A0A0A"/>',
        '<g fill="none" stroke="#555555" stroke-width="1.5">',
        *(f'<path d="{connection}"/>' for connection, _ in connections),
        "</g>",
        '<g fill="none" stroke-width="3">',
        *(
            f'<path class="signal" d="{connection}" stroke="{accent}"/>'
            for connection, accent in connections
        ),
        "</g>",
        '<g fill="#888888" font-family="monospace" font-size="11">',
        '<text x="249" y="77">Terraform</text>',
        '<text x="584" y="94">public</text>',
        "</g>",
    ]
    for left, top, title, subtitle, accent in nodes:
        elements.extend(
            [
                f'<rect x="{left}" y="{top}" width="198" height="46" rx="3" fill="#111111" stroke="{accent}"/>',
                f'<text x="{left + 99}" y="{top + 19}" text-anchor="middle" fill="#F5F5F0" font-family="monospace" font-size="14">{title}</text>',
                f'<text x="{left + 99}" y="{top + 35}" text-anchor="middle" fill="#888888" font-family="monospace" font-size="11">{subtitle}</text>',
            ]
        )
    elements.append("</svg>")
    destination.write_text("\n".join(elements) + "\n")


def main():
    destination = Path(__file__).parent / "scene" / "assets"
    record_ambient_canvas(destination / "ambient-canvas.gif")
    write_site_architecture(destination / "site-architecture.svg")


if __name__ == "__main__":
    main()
