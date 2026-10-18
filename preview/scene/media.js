async function mountProfileReadmeMedia(assets) {
  const article = document.querySelector("article.markdown-body");
  const images = [...article.querySelectorAll("img")];
  const animatedImages = [];
  const animatedVectors = [];
  const vectorTimelines = [];
  const restorations = [];

  try {
    for (const asset of assets) {
      const image = images.find(
        (candidate) =>
          candidate.currentSrc === asset.source &&
          candidate.getBoundingClientRect().width,
      );
      if (!image) throw new Error(`Animated image is missing: ${asset.source}`);

      if (asset.frames) {
        const frames = await Promise.all(
          asset.frames.map(async (frame) => {
            const decoded = new Image();
            decoded.src = frame.source;
            await decoded.decode();
            return { end: frame.end, image: decoded };
          }),
        );
        const originalSource = image.getAttribute("src");
        const originalSourceSet = image.getAttribute("srcset");
        restorations.push(() => {
          image.setAttribute("src", originalSource);
          if (originalSourceSet !== null)
            image.setAttribute("srcset", originalSourceSet);
        });
        image.removeAttribute("srcset");
        animatedImages.push({ image, frames, duration: asset.duration });
        continue;
      }

      const host = document.createElement("span");
      const style = getComputedStyle(image);
      for (const property of [
        "display",
        "width",
        "height",
        "max-width",
        "padding",
        "margin",
        "box-sizing",
        "vertical-align",
        "float",
      ])
        host.style.setProperty(property, style.getPropertyValue(property));
      host.style.display = "inline-block";
      const shadow = host.attachShadow({ mode: "open" });
      shadow.innerHTML = asset.svg;
      const vector = shadow.querySelector("svg");
      vector.style.width = "100%";
      vector.style.height = "100%";
      vector.pauseAnimations();
      vector.setCurrentTime(0);
      image.replaceWith(host);
      restorations.push(() => host.replaceWith(image));
      vector.getBoundingClientRect();
      const animations = vector.getAnimations({ subtree: true });
      if (!animations.length)
        throw new Error(`SVG has no CSS animations: ${asset.source}`);
      for (const animation of animations) {
        animation.pause();
        animation.currentTime = 0;
      }
      await Promise.all(animations.map((animation) => animation.ready));
      animatedVectors.push(...animations);
      vectorTimelines.push(vector);
    }

    window.profileReadmeMedia = {
      async seek(milliseconds) {
        for (const vector of vectorTimelines)
          vector.setCurrentTime(milliseconds / 1000);
        for (const animation of animatedVectors)
          animation.currentTime = milliseconds;
        await Promise.all(
          animatedImages.map(async ({ image, frames, duration }) => {
            const elapsed = milliseconds % duration;
            const frame = frames.find((candidate) => elapsed < candidate.end);
            if (image.src === frame.image.src) return;
            image.src = frame.image.src;
            await image.decode();
          }),
        );
      },
      restore() {
        for (const restore of restorations.reverse()) restore();
        delete window.profileReadmeMedia;
      },
    };
    await window.profileReadmeMedia.seek(0);
  } catch (error) {
    for (const restore of restorations.reverse()) restore();
    delete window.profileReadmeMedia;
    throw error;
  }
}
