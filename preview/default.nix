{
  pkgs ? import <nixpkgs> { },
}:
pkgs.mkShell {
  packages = [
    (pkgs.python312.withPackages (packages: [
      packages.pillow
      packages.markdown-it-py
      packages.websockets
    ]))
    pkgs.ffmpeg
  ];
}
