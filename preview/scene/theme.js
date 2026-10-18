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
