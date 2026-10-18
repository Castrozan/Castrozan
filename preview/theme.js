async function applyProfileTheme(theme) {
  const root = document.documentElement;
  const stylesheet = document.querySelector(
    `link[data-color-theme="${theme}"]`,
  );
  if (stylesheet && !stylesheet.getAttribute("href")) {
    await new Promise((resolve, reject) => {
      stylesheet.addEventListener("load", resolve, { once: true });
      stylesheet.addEventListener("error", reject, { once: true });
      stylesheet.href = stylesheet.dataset.href;
    });
  }
  root.dataset.colorMode = theme;
  root.dataset.lightTheme = "light";
  root.dataset.darkTheme = "dark";
  await document.fonts.ready;
  await Promise.all(
    [...document.querySelectorAll("article.markdown-body img")].map((image) =>
      image.decode(),
    ),
  );
  const leadingParagraph = document.querySelector(
    "article.markdown-body",
  ).firstElementChild;
  const leadingImages = [...leadingParagraph.querySelectorAll("img")];
  if (
    leadingParagraph.matches("p") &&
    !leadingParagraph.textContent.trim() &&
    leadingImages.length &&
    leadingImages.every((image) => !image.getBoundingClientRect().width)
  ) {
    leadingParagraph.remove();
  }
  return getComputedStyle(document.body).backgroundColor;
}

function applyProfileMediaTheme(assets, theme) {
  if (theme !== "light") return assets;
  const themeColors = getComputedStyle(document.documentElement);
  const palette = {
    "#0d1117": "--bgColor-default",
    "#30363d": "--borderColor-default",
    "#e6edf3": "--fgColor-default",
    "#9198a1": "--fgColor-muted",
    "#58a6ff": "--fgColor-accent",
    "#161b22": "--contribution-default-bgColor-0",
    "#0e4429": "--contribution-default-bgColor-1",
    "#006d32": "--contribution-default-bgColor-2",
    "#26a641": "--contribution-default-bgColor-3",
    "#39d353": "--contribution-default-bgColor-4",
  };
  return assets.map((asset) => {
    if (!asset.svg) return asset;
    const svg = asset.svg.replace(/#[0-9a-f]{6}/gi, (color) =>
      palette[color.toLowerCase()]
        ? themeColors.getPropertyValue(palette[color.toLowerCase()]).trim()
        : color,
    );
    return { ...asset, svg };
  });
}
