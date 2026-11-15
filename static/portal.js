(() => {
  "use strict";
  const gate = document.getElementById("authGate");
  const canvas = document.getElementById("portalStars");
  if (!gate || !canvas) return;

  const ctx = canvas.getContext("2d");
  if (!ctx) return;

  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const pointerFine = window.matchMedia("(pointer: fine)").matches;
  const cursor = gate.querySelector(".portal-cursor");
  let width = 0, height = 0, dpr = 1, stars = [], frame = 0;
  let pointerX = .55, pointerY = .45, targetX = .55, targetY = .45;

  function resize() {
    const rect = gate.getBoundingClientRect();
    width = Math.max(1, rect.width);
    height = Math.max(1, rect.height);
    dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = Math.round(width * dpr);
    canvas.height = Math.round(height * dpr);
    canvas.style.width = width + "px";
    canvas.style.height = height + "px";
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    const count = Math.min(170, Math.max(65, Math.floor(width * height / 8500)));
    stars = Array.from({ length: count }, (_, i) => ({
      x: Math.random() * width,
      y: Math.random() * height,
      r: Math.random() * 1.15 + .2,
      a: Math.random() * .52 + .12,
      p: Math.random() * Math.PI * 2,
      speed: Math.random() * .008 + .002,
      warm: i % 9 === 0
    }));
    draw();
  }

  function draw() {
    if (!ctx) return;
    ctx.clearRect(0, 0, width, height);
    const px = (pointerX - .5) * 13;
    const py = (pointerY - .5) * 13;

    for (const s of stars) {
      const twinkle = reducedMotion ? 1 : .72 + Math.sin(frame * s.speed + s.p) * .28;
      const x = s.x + px * s.r;
      const y = s.y + py * s.r;
      ctx.beginPath();
      ctx.arc(x, y, s.r, 0, Math.PI * 2);
      ctx.fillStyle = s.warm
        ? `rgba(216,189,120,${s.a * twinkle})`
        : `rgba(190,211,194,${s.a * twinkle})`;
      ctx.fill();
    }

    if (!reducedMotion) {
      frame++;
      pointerX += (targetX - pointerX) * .045;
      pointerY += (targetY - pointerY) * .045;
      requestAnimationFrame(draw);
    }
  }

  function move(event) {
    const rect = gate.getBoundingClientRect();
    targetX = Math.max(0, Math.min(1, (event.clientX - rect.left) / rect.width));
    targetY = Math.max(0, Math.min(1, (event.clientY - rect.top) / rect.height));
    gate.style.setProperty("--pointer-x", (targetX * 100) + "%");
    gate.style.setProperty("--pointer-y", (targetY * 100) + "%");

    if (cursor) {
      cursor.style.left = event.clientX + "px";
      cursor.style.top = event.clientY + "px";
      cursor.classList.add("is-visible");
    }
  }

  if (pointerFine) {
    gate.addEventListener("pointermove", move, { passive: true });
    gate.addEventListener("pointerleave", () => cursor && cursor.classList.remove("is-visible"));
  }

  window.addEventListener("resize", resize, { passive: true });
  resize();
})();