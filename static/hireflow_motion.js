(() => {
  try {
    window.frameElement?.setAttribute("aria-hidden", "true");
    window.frameElement?.setAttribute("tabindex", "-1");
    const host = window.parent;
    const doc = host.document;
    const root = doc.documentElement;
    if (root.dataset.hireflowMotion === "v2") {
      host.HireFlowMotion?.refresh();
      return;
    }

    const reduced = host.matchMedia("(prefers-reduced-motion: reduce)");
    const finePointer = host.matchMedia("(hover: hover) and (pointer: fine)");
    const mayMove = () => !reduced.matches && finePointer.matches;
    let refreshFrame = 0;
    let scrollFrame = 0;
    let pointerFrame = 0;
    let pointerEvent = null;
    let drag = null;
    const clamp = (value, minimum, maximum) => Math.min(maximum, Math.max(minimum, value));

    function rotateScene(scene, x, y, locked = false) {
      const core = scene?.querySelector(".hf-scene-core");
      if (!core || reduced.matches) return;
      const pitch = clamp(x, -26, 26);
      const yaw = clamp(y, -32, 32);
      core.style.setProperty("--rx", `${pitch.toFixed(2)}deg`);
      core.style.setProperty("--ry", `${yaw.toFixed(2)}deg`);
      scene.dataset.rx = String(pitch);
      scene.dataset.ry = String(yaw);
      if (locked) scene.dataset.locked = "true";
    }

    function sceneAngles(scene) {
      return [Number(scene.dataset.rx ?? -8), Number(scene.dataset.ry ?? -11)];
    }

    const revealObserver = "IntersectionObserver" in host
      ? new host.IntersectionObserver((entries) => {
          for (const entry of entries) {
            if (entry.isIntersecting) {
              entry.target.classList.add("is-visible");
              revealObserver.unobserve(entry.target);
            }
          }
        }, { threshold: 0.12, rootMargin: "0px 0px -6% 0px" })
      : null;

    function updateScrollScene() {
      scrollFrame = 0;
      const progress = doc.querySelector(".landing-scroll-progress");
      if (progress) {
        const page = doc.scrollingElement;
        const main = doc.querySelector('[data-testid="stMain"]');
        const view = doc.querySelector('[data-testid="stAppViewContainer"]');
        const source = [main, view, page].find((element) => element && element.scrollHeight - element.clientHeight > 10) || page;
        const maximum = Math.max(1, source.scrollHeight - source.clientHeight);
        progress.style.transform = `scaleX(${Math.min(1, Math.max(0, source.scrollTop / maximum)).toFixed(4)})`;
      }

      const story = doc.querySelector(".motion-story");
      if (!story) return;
      const chapters = [...story.querySelectorAll(".motion-chapter")];
      let active = 1;
      for (const chapter of chapters) {
        if (chapter.getBoundingClientRect().top < host.innerHeight * 0.57) {
          active = Number(chapter.dataset.step) || active;
        }
      }
      const step = String(active);
      if (story.dataset.step === step) return;
      story.dataset.step = step;
      const stage = story.querySelector(".story-stage");
      if (stage) stage.dataset.step = step;
      for (const visual of story.querySelectorAll(".story-visual")) {
        visual.setAttribute("aria-hidden", visual.dataset.step === step ? "false" : "true");
      }
      const number = story.querySelector(".story-step-number");
      if (number) number.textContent = `0${active} / 03`;
    }

    function scheduleScroll() {
      if (!scrollFrame) scrollFrame = host.requestAnimationFrame(updateScrollScene);
    }

    function refresh() {
      refreshFrame = 0;
      const isPublic = Boolean(doc.querySelector(".landing-copy"));
      root.classList.toggle("hf-public", isPublic);
      if (revealObserver && !reduced.matches) {
        root.classList.add("hf-motion-ready");
        for (const element of doc.querySelectorAll(".hf-reveal:not([data-motion-observed])")) {
          element.dataset.motionObserved = "true";
          revealObserver.observe(element);
        }
      } else {
        root.classList.remove("hf-motion-ready");
      }
      scheduleScroll();
    }

    function scheduleRefresh() {
      if (!refreshFrame) refreshFrame = host.requestAnimationFrame(refresh);
    }

    function moveDecorativeObject() {
      pointerFrame = 0;
      const event = pointerEvent;
      if (!event || !mayMove() || !(event.target instanceof host.Element)) return;
      const surface = event.target.closest(".login-visual, .workspace-hero, .mode-copy, .studio-hero");
      const object = surface?.querySelector(".motion-object");
      if (!object) return;
      const bounds = surface.getBoundingClientRect();
      const x = ((event.clientX - bounds.left) / bounds.width - 0.5) * 16;
      const y = ((event.clientY - bounds.top) / bounds.height - 0.5) * 12;
      object.style.transform = `translate3d(${x.toFixed(1)}px, ${y.toFixed(1)}px, 0)`;
    }

    doc.addEventListener("pointermove", (event) => {
      pointerEvent = event;
      if (mayMove() && !pointerFrame) pointerFrame = host.requestAnimationFrame(moveDecorativeObject);
      if (!mayMove() || !(event.target instanceof host.Element)) return;
      const scene = drag?.scene ?? event.target.closest(".hf-3d-scene");
      if (!scene) return;
      if (drag) {
        rotateScene(scene, drag.rx - (event.clientY - drag.y) * .13, drag.ry + (event.clientX - drag.x) * .16, true);
      } else if (scene.dataset.locked !== "true") {
        const bounds = scene.getBoundingClientRect();
        const rx = -8 - ((event.clientY - bounds.top) / bounds.height - .5) * 13;
        const ry = -11 + ((event.clientX - bounds.left) / bounds.width - .5) * 19;
        rotateScene(scene, rx, ry);
      }
    }, { passive: true });

    doc.addEventListener("pointerout", (event) => {
      const scene = event.target?.closest?.(".hf-3d-scene");
      if (scene && !scene.contains(event.relatedTarget) && !drag && scene.dataset.locked !== "true") rotateScene(scene, -8, -11);
      const surface = event.target?.closest?.(".login-visual, .workspace-hero, .mode-copy, .studio-hero");
      if (!surface || surface.contains(event.relatedTarget)) return;
      const object = surface.querySelector(".motion-object");
      if (object) object.style.transform = "";
    }, { passive: true });

    doc.addEventListener("pointerdown", (event) => {
      if (mayMove() && event.target instanceof host.Element) {
        const scene = event.target.closest(".hf-3d-scene");
        if (scene && event.button === 0) {
          const [rx, ry] = sceneAngles(scene);
          drag = { scene, x: event.clientX, y: event.clientY, rx, ry };
          scene.classList.add("is-dragging");
          scene.setPointerCapture?.(event.pointerId);
        }
      }
      if (reduced.matches || !(event.target instanceof host.Element)) return;
      const button = event.target.closest("button");
      if (!button || button.disabled || !button.matches(".stButton button, .stFormSubmitButton button, .stDownloadButton button")) return;
      const bounds = button.getBoundingClientRect();
      const pulse = doc.createElement("span");
      pulse.className = "hf-ink-pulse";
      pulse.setAttribute("aria-hidden", "true");
      const diameter = Math.max(bounds.width, bounds.height) * 2;
      pulse.style.width = `${diameter}px`;
      pulse.style.height = `${diameter}px`;
      pulse.style.left = `${event.clientX - bounds.left - diameter / 2}px`;
      pulse.style.top = `${event.clientY - bounds.top - diameter / 2}px`;
      button.append(pulse);
      pulse.addEventListener("animationend", () => pulse.remove(), { once: true });
    }, { passive: true });

    doc.addEventListener("pointerup", () => {
      if (!drag) return;
      drag.scene.classList.remove("is-dragging");
      drag = null;
    }, { passive: true });
    doc.addEventListener("pointercancel", () => {
      if (!drag) return;
      drag.scene.classList.remove("is-dragging");
      drag = null;
    }, { passive: true });
    doc.addEventListener("keydown", (event) => {
      const scene = event.target?.closest?.(".hf-3d-scene");
      if (!scene || reduced.matches) return;
      const [rx, ry] = sceneAngles(scene);
      const angles = {
        ArrowUp: [rx + 5, ry], ArrowDown: [rx - 5, ry],
        ArrowLeft: [rx, ry - 5], ArrowRight: [rx, ry + 5], Home: [-8, -11],
      }[event.key];
      if (!angles) return;
      event.preventDefault();
      rotateScene(scene, ...angles, event.key !== "Home");
      if (event.key === "Home") delete scene.dataset.locked;
    });
    doc.addEventListener("click", (event) => {
      if (!event.target?.closest?.(".scene-reset")) return;
      const scene = doc.querySelector(".hf-3d-scene");
      if (!scene) return;
      delete scene.dataset.locked;
      rotateScene(scene, -8, -11);
      scene.focus({ preventScroll: true });
    });

    doc.addEventListener("scroll", scheduleScroll, { passive: true, capture: true });
    host.addEventListener("resize", scheduleScroll, { passive: true });
    reduced.addEventListener("change", scheduleRefresh);
    new host.MutationObserver(scheduleRefresh).observe(doc.body, { childList: true, subtree: true });
    host.HireFlowMotion = { refresh: scheduleRefresh };
    root.dataset.hireflowMotion = "v2";
    refresh();
  } catch (_) {
    // Native Streamlit controls remain usable if the embedding context is isolated.
  }
})();
