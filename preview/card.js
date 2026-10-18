function mountProfileReadmeCard(reverseHtml) {
  const originalArticle = document.querySelector("article.markdown-body");
  if (!originalArticle) throw new Error("The profile README is missing");

  const originalParent = originalArticle.parentElement;
  const originalNextSibling = originalArticle.nextSibling;
  const rectangle = originalArticle.getBoundingClientRect();
  const backgroundColor = getComputedStyle(document.body).backgroundColor;
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
    height: `${rectangle.height}px`,
    zIndex: "2147483647",
    perspective: `${rectangle.width * 4}px`,
    overflow: "hidden",
    backgroundColor,
    pointerEvents: "none",
  });
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
      backgroundColor,
    });
  }
  reverse.style.transform = "rotateY(180deg)";
  reverseArticle.innerHTML = reverseHtml;
  front.append(originalArticle);
  reverse.append(reverseArticle);
  card.append(front, reverse);
  stage.append(card);
  document.body.append(stage);

  if (reverseArticle.scrollHeight > rectangle.height) {
    originalParent.insertBefore(originalArticle, originalNextSibling);
    stage.remove();
    throw new Error("The reverse content exceeds the captured README height");
  }

  const keyframes = [];
  for (let milliseconds = 0; milliseconds <= 20000; milliseconds += 20) {
    let rotation = 0;
    let scale = 1;
    let progress = null;
    if (milliseconds >= 9200 && milliseconds <= 10800) {
      progress = (milliseconds - 9200) / 1600;
    } else if (milliseconds > 10800 && milliseconds < 18400) {
      rotation = 180;
    } else if (milliseconds >= 18400) {
      progress = (milliseconds - 18400) / 1600;
      rotation = 180;
    }
    if (progress !== null) {
      const easedProgress =
        progress * progress * progress * (progress * (progress * 6 - 15) + 10);
      rotation += 180 * easedProgress;
      scale = 1 - 0.16 * Math.sin(Math.PI * easedProgress);
    }
    keyframes.push({
      offset: milliseconds / 20000,
      transform: `rotateY(${rotation}deg) scale(${scale})`,
    });
  }

  const animation = card.animate(keyframes, {
    duration: 20000,
    iterations: 1,
    fill: "both",
  });
  animation.pause();
  animation.currentTime = 0;

  window.profileReadmeCard = {
    animation,
    async showRecordedFaces(frontSource, reverseSource) {
      animation.pause();
      const images = [frontSource, reverseSource].map((source) => {
        const image = new Image();
        image.src = source;
        Object.assign(image.style, {
          width: "100%",
          height: "100%",
          display: "block",
        });
        return image;
      });
      await Promise.all(images.map((image) => image.decode()));
      front.replaceChildren(images[0]);
      reverse.replaceChildren(images[1]);
    },
    restore() {
      animation.cancel();
      originalParent.insertBefore(originalArticle, originalNextSibling);
      stage.remove();
      delete window.profileReadmeCard;
    },
  };

  return {
    width: Math.round(rectangle.width),
    height: Math.round(rectangle.height),
    backgroundColor,
    reverseHeight: reverseArticle.scrollHeight,
  };
}
