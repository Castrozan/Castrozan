async function arrangeProfileFront(snakeSource, stylesheet) {
  const article = document.querySelector("article.markdown-body");
  const languageRows = [
    ...article
      .querySelector("pre")
      .textContent.matchAll(/^(\w+)\s+[^\n]*?([\d.]+)\s*%/gm),
  ];
  const logo = [...article.querySelectorAll("img")].find(
    (image) =>
      image.currentSrc.includes("nix-") && image.getBoundingClientRect().width,
  );
  const logoLink = logo.closest("a").cloneNode(true);
  const badges = article
    .querySelector('img[data-canonical-src*="img.shields.io"]')
    .closest("p")
    .cloneNode(true);
  badges.className = "profile-badges";
  const firstDivider = article.querySelector("hr");
  while (article.firstChild !== firstDivider) article.firstChild.remove();
  const header = document.createElement("div");
  header.className = "profile-overview";
  header.innerHTML = `<div class="profile-languages"><h3>Languages</h3>${languageRows.map(([, name, percentage]) => `<div class="language-row"><span>${name}</span><div><i style="width:${percentage}%"></i></div><span>${Number(percentage).toFixed(2)}%</span></div>`).join("")}</div><div class="profile-builds"><h3>What I build</h3><a href="https://github.com/Castrozan/.dotfiles">Declarative systems</a><p>NixOS, macOS and a workspace I can rebuild.</p><a href="https://github.com/Castrozan/clawde">Tools for agents & people</a><p>Persistent agents, local voice input and the glue between them.</p></div>`;
  header.prepend(logoLink);
  article.prepend(header, badges);
  article.classList.add("profile-front");
  const style = document.createElement("style");
  style.textContent = stylesheet;
  document.head.append(style);
  const snake = article.querySelector('img[src*="gitlab-snk"]');
  snake.src = snakeSource;
  snake.removeAttribute("srcset");
  await snake.decode();
}
