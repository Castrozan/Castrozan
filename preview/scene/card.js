async function mountProfileReadmeCard(reverseFace, timing) {
  const originalArticle = document.querySelector("article.markdown-body");
  if (!originalArticle) throw new Error("The profile README is missing");

  const bodyContents = Array.from(document.body.childNodes);
  const originalParent = originalArticle.parentElement;
  const originalNextSibling = originalArticle.nextSibling;
  const rectangle = originalArticle.getBoundingClientRect();
  if (rectangle.width !== reverseFace.width)
    throw new Error(
      `The Markdown faces have different native widths: ${rectangle.width} and ${reverseFace.width}`,
    );
  const height = Math.ceil(Math.max(rectangle.height, reverseFace.height));
  const stage = document.createElement("div");
  const card = document.createElement("div");
  const front = document.createElement("div");
  const reverse = document.createElement("div");
  const reverseArticle = originalArticle.cloneNode(false);

  Object.assign(stage.style, {
    position: "fixed",
    left: "0",
    top: "0",
    width: `${rectangle.width}px`,
    height: `${height}px`,
    zIndex: "2147483647",
    perspective: `${rectangle.width * 4}px`,
    overflow: "hidden",
    pointerEvents: "none",
  });
  for (const backgroundVariable of [
    "--bgColor-default",
    "--bgColor-muted",
    "--bgColor-neutral-muted",
  ]) {
    stage.style.setProperty(backgroundVariable, "transparent");
  }
  Object.assign(card.style, {
    position: "relative",
    width: "100%",
    height: "100%",
    transformStyle: "preserve-3d",
  });
  for (const face of [front, reverse]) {
    Object.assign(face.style, {
      position: "absolute",
      inset: "0",
      backfaceVisibility: "hidden",
    });
  }
  reverse.style.transform = "rotateY(180deg)";
  reverseArticle.innerHTML = reverseFace.html;
  front.dataset.readmeFace = "front";
  reverse.dataset.readmeFace = "back";
  front.append(originalArticle);
  reverse.append(reverseArticle);
  card.append(front, reverse);
  stage.append(card);
  document.body.append(stage);
  await Promise.all(
    [...reverseArticle.querySelectorAll("img")].map((image) => image.decode()),
  );

  if (reverseArticle.scrollHeight > height) {
    originalParent.insertBefore(originalArticle, originalNextSibling);
    stage.remove();
    throw new Error("The reverse content exceeds the captured README height");
  }

  document.body.replaceChildren(stage);

  const keyframes = [];
  const outgoingEnd = timing.outgoingStart + timing.turnDuration;
  for (
    let milliseconds = 0;
    milliseconds <= timing.duration;
    milliseconds += 20
  ) {
    let rotation = 0;
    let scale = 1;
    let progress = null;
    if (milliseconds >= timing.outgoingStart && milliseconds <= outgoingEnd) {
      progress = (milliseconds - timing.outgoingStart) / timing.turnDuration;
    } else if (
      milliseconds > outgoingEnd &&
      milliseconds < timing.returnStart
    ) {
      rotation = 180;
    } else if (milliseconds >= timing.returnStart) {
      progress = (milliseconds - timing.returnStart) / timing.turnDuration;
      rotation = 180;
    }
    if (progress !== null) {
      const easedProgress =
        progress * progress * progress * (progress * (progress * 6 - 15) + 10);
      rotation += 180 * easedProgress;
      scale = 1 - 0.16 * Math.sin(Math.PI * easedProgress);
    }
    keyframes.push({
      offset: milliseconds / timing.duration,
      transform: `rotateY(${-rotation}deg) scale(${scale})`,
    });
  }

  const animation = card.animate(keyframes, {
    duration: timing.duration,
    iterations: 1,
    fill: "both",
  });
  animation.pause();
  animation.currentTime = 0;

  window.profileReadmeCard = {
    animation,
    restore() {
      animation.cancel();
      document.body.replaceChildren(...bodyContents);
      originalParent.insertBefore(originalArticle, originalNextSibling);
      delete window.profileReadmeCard;
    },
  };

  return {
    width: Math.round(rectangle.width),
    height,
    reverseHeight: reverseArticle.scrollHeight,
  };
}
