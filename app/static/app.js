const form = document.querySelector("#analysis-form");
const textarea = document.querySelector("#comment");
const characterCount = document.querySelector("#character-count");
const results = document.querySelector("#results");
const errorMessage = document.querySelector("#form-error");
const submitButton = form?.querySelector(".analyze-button");
const analysisState = document.querySelector("#analysis-state");

const verdictCopy = {
  clear: {
    title: "No strong risk signal",
    text: "All six probabilities are below the review range.",
  },
  watch: {
    title: "Weak signal detected",
    text: "The model found an uncertain pattern. Check the surrounding context.",
  },
  review: {
    title: "Human review recommended",
    text: "At least one label crossed the review threshold.",
  },
  high_risk: {
    title: "Strong risk signal detected",
    text: "Prioritize this comment for contextual review.",
  },
};

function updateCount() {
  if (!textarea || !characterCount) return;
  characterCount.textContent = `${textarea.value.length} / ${textarea.maxLength}`;
}

function setState(state, label) {
  if (!analysisState) return;
  analysisState.className = `analysis-state is-${state}`;
  analysisState.innerHTML = `<i aria-hidden="true"></i>${label}`;
}

function setLoading(loading) {
  if (!submitButton) return;
  submitButton.disabled = loading;
  submitButton.querySelector("span").textContent = loading
    ? "Analyzing..."
    : "Analyze comment";
  setState(loading ? "loading" : "ready", loading ? "Running model" : "Analysis complete");
}

function renderResults(payload) {
  const verdict = verdictCopy[payload.verdict] || verdictCopy.review;
  const percent = Math.round(payload.top_score * 100);

  document.querySelector("#verdict-title").textContent = verdict.title;
  document.querySelector("#result-explanation").textContent = verdict.text;
  document.querySelector("#risk-score").textContent = `${percent}%`;
  results.dataset.verdict = payload.verdict;

  Object.entries(payload.scores).forEach(([label, score]) => {
    const row = document.querySelector(`[data-label="${label}"]`);
    if (!row) return;
    const scorePercent = Math.round(score * 1000) / 10;
    row.querySelector("strong").textContent = `${scorePercent.toFixed(1)}%`;
    row.querySelector("i").style.width = `${scorePercent}%`;
  });

  setState("ready", "Analysis complete");
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
    setState("error", "Analysis failed");
  } finally {
    submitButton.disabled = false;
    submitButton.querySelector("span").textContent = "Analyze comment";
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

updateCount();
