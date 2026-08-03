const form = document.querySelector("#analysis-form");
const textarea = document.querySelector("#comment");
const characterCount = document.querySelector("#character-count");
const results = document.querySelector("#results");
const errorMessage = document.querySelector("#form-error");
const submitButton = form?.querySelector(".analyze-button");

const verdictCopy = {
  clear: {
    title: "No strong risk signal",
    text: "All six probabilities are below the watch range. Contextual review may still be appropriate.",
  },
  watch: {
    title: "A weak signal is present",
    text: "The model found an uncertain pattern. Review the surrounding conversation before deciding.",
  },
  review: {
    title: "Human review recommended",
    text: "At least one risk signal crossed the configured threshold. Treat this as evidence, not a final verdict.",
  },
  high_risk: {
    title: "Strong risk signal detected",
    text: "The leading signal is high confidence. Prioritize this comment for contextual review.",
  },
};

function updateCount() {
  if (!textarea || !characterCount) return;
  characterCount.textContent = `${textarea.value.length} / ${textarea.maxLength}`;
}

function setLoading(loading) {
  if (!submitButton) return;
  submitButton.disabled = loading;
  submitButton.classList.toggle("is-loading", loading);
  submitButton.querySelector("span").textContent = loading
    ? "Loading model and analyzing"
    : "Run six-signal analysis";
}

function renderResults(payload) {
  const verdict = verdictCopy[payload.verdict] || verdictCopy.review;
  const percent = Math.round(payload.top_score * 100);

  document.querySelector("#verdict-title").textContent = verdict.title;
  document.querySelector("#result-explanation").textContent = verdict.text;
  document.querySelector("#risk-score").textContent = `${percent}%`;
  document.querySelector("#risk-dial").style.setProperty("--risk", percent);
  results.dataset.verdict = payload.verdict;

  Object.entries(payload.scores).forEach(([label, score]) => {
    const row = document.querySelector(`[data-label="${label}"]`);
    if (!row) return;
    const scorePercent = Math.round(score * 1000) / 10;
    row.querySelector("strong").textContent = `${scorePercent.toFixed(1)}%`;
    row.querySelector("i").style.width = `${scorePercent}%`;
  });

  form.hidden = true;
  results.hidden = false;
  results.setAttribute("aria-hidden", "false");
  if (window.gsap) {
    gsap.fromTo(results, { opacity: 0, y: 24 }, { opacity: 1, y: 0, duration: 0.65, ease: "power3.out" });
    gsap.fromTo(".score-track i", { width: 0 }, { width: (index, target) => target.style.width, duration: 0.9, stagger: 0.07, ease: "power3.out" });
  }
}

form?.addEventListener("submit", async (event) => {
  event.preventDefault();
  errorMessage.textContent = "";
  setLoading(true);

  try {
    const response = await fetch("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: textarea.value }),
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || "Analysis failed. Please try again.");
    renderResults(payload);
  } catch (error) {
    errorMessage.textContent = error.message;
  } finally {
    setLoading(false);
  }
});

textarea?.addEventListener("input", updateCount);

document.querySelectorAll("[data-sample]").forEach((button) => {
  button.addEventListener("click", () => {
    textarea.value = button.dataset.sample;
    updateCount();
    textarea.focus();
  });
});

document.querySelector("#reset-analysis")?.addEventListener("click", () => {
  results.hidden = true;
  results.setAttribute("aria-hidden", "true");
  form.hidden = false;
  textarea.focus();
});

document.querySelectorAll(".method-step button").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll(".method-step").forEach((step) => {
      const active = step === button.closest(".method-step");
      step.classList.toggle("is-active", active);
      step.querySelector("button").setAttribute("aria-expanded", String(active));
    });
  });
});

function initializeMotion() {
  if (!window.gsap || !window.ScrollTrigger) return;
  gsap.registerPlugin(ScrollTrigger);

  gsap.from(".site-header", { y: -32, opacity: 0, duration: 0.8, ease: "power3.out" });
  gsap.from(".hero-copy > *", { y: 42, opacity: 0, duration: 0.9, stagger: 0.1, ease: "power3.out" });
  gsap.from(".analyzer-wrap", { y: 58, scale: 0.96, opacity: 0, duration: 1.1, delay: 0.2, ease: "power3.out" });

  gsap.utils.toArray("[data-reveal]:not(.hero-copy):not(.analyzer-wrap)").forEach((element) => {
    gsap.from(element, {
      y: 70,
      opacity: 0,
      duration: 1,
      ease: "power3.out",
      scrollTrigger: { trigger: element, start: "top 84%" },
    });
  });

  const splitCopy = document.querySelector("[data-split-text]");
  if (splitCopy) {
    const phrase = splitCopy.textContent.trim();
    splitCopy.setAttribute("aria-label", phrase);
    splitCopy.innerHTML = phrase
      .split(/\s+/)
      .map((word) => `<span aria-hidden="true">${word}</span>`)
      .join(" ");
    gsap.fromTo(
      splitCopy.querySelectorAll("span"),
      { opacity: 0.12 },
      {
        opacity: 1,
        stagger: 0.05,
        scrollTrigger: {
          trigger: splitCopy,
          start: "top 78%",
          end: "bottom 52%",
          scrub: 1,
        },
      },
    );
  }

  ScrollTrigger.matchMedia({
    "(min-width: 901px)": () => {
      ScrollTrigger.create({
        trigger: ".method",
        start: "top 18%",
        end: "bottom 72%",
        pin: ".method-intro",
        pinSpacing: false,
      });
    },
  });
}

window.addEventListener("load", initializeMotion);
updateCount();
