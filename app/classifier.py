"""Inference layer for VerityGuard's six-label toxicity classifier."""

from __future__ import annotations

import os
import threading
from dataclasses import asdict, dataclass
from typing import Any


MODEL_NAME = os.getenv("MODEL_NAME", "unitary/toxic-bert")
LABELS = (
    "toxic",
    "severe_toxic",
    "obscene",
    "threat",
    "insult",
    "identity_hate",
)

LABEL_COPY = {
    "toxic": {
        "name": "Toxic language",
        "description": "Rude, disrespectful, or unreasonable language.",
    },
    "severe_toxic": {
        "name": "Severe toxicity",
        "description": "Highly aggressive or deliberately harmful language.",
    },
    "obscene": {
        "name": "Obscene content",
        "description": "Explicit profanity or sexually vulgar language.",
    },
    "threat": {
        "name": "Threat",
        "description": "Language expressing intent to harm or intimidate.",
    },
    "insult": {
        "name": "Insult",
        "description": "A direct attack on a person or group.",
    },
    "identity_hate": {
        "name": "Identity hate",
        "description": "Hostility aimed at a protected identity or group.",
    },
}


class ClassifierUnavailable(RuntimeError):
    """Raised when the configured model cannot be loaded or validated."""


@dataclass(frozen=True)
class AnalysisResult:
    text: str
    scores: dict[str, float]
    top_label: str
    top_score: float
    verdict: str
    flagged: bool
    threshold: float

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["labels"] = LABEL_COPY
        return payload


class ToxicityClassifier:
    """Lazy-loaded, thread-safe multi-label BERT classifier.

    The original project trained one binary output but displayed six labels.
    This implementation validates that the loaded checkpoint exposes all six
    expected labels and applies sigmoid independently to every logit.
    """

    def __init__(
        self,
        model_name: str = MODEL_NAME,
        threshold: float = 0.50,
        max_length: int = 256,
    ) -> None:
        if not 0 < threshold < 1:
            raise ValueError("threshold must be between 0 and 1")

        self.model_name = model_name
        self.threshold = threshold
        self.max_length = max_length
        self._tokenizer: Any | None = None
        self._model: Any | None = None
        self._torch: Any | None = None
        self._device = "cpu"
        self._label_order: tuple[str, ...] = LABELS
        self._load_lock = threading.Lock()

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    def _ensure_loaded(self) -> None:
        if self.is_loaded:
            return

        with self._load_lock:
            if self.is_loaded:
                return

            try:
                import torch
                from transformers import AutoModelForSequenceClassification, AutoTokenizer

                self._device = "cuda" if torch.cuda.is_available() else "cpu"
                self._tokenizer = AutoTokenizer.from_pretrained(self.model_name)
                self._model = AutoModelForSequenceClassification.from_pretrained(
                    self.model_name
                )
                self._model.to(self._device)
                self._model.eval()
                self._torch = torch
                self._label_order = self._resolve_label_order(self._model.config.id2label)
            except ClassifierUnavailable:
                raise
            except Exception as exc:
                self._tokenizer = None
                self._model = None
                self._torch = None
                raise ClassifierUnavailable(
                    f"Could not load model '{self.model_name}'."
                ) from exc

    @staticmethod
    def _resolve_label_order(id2label: dict[Any, str]) -> tuple[str, ...]:
        ordered = tuple(
            str(id2label[key]).strip().lower().replace(" ", "_")
            for key in sorted(id2label, key=lambda value: int(value))
        )

        if ordered == tuple(f"label_{index}" for index in range(len(LABELS))):
            return LABELS

        if len(ordered) != len(LABELS) or set(ordered) != set(LABELS):
            raise ClassifierUnavailable(
                "The model label contract is incompatible. Expected: "
                + ", ".join(LABELS)
            )
        return ordered

    def predict(self, text: str) -> AnalysisResult:
        clean_text = " ".join(text.split())
        if not clean_text:
            raise ValueError("Text cannot be empty.")

        self._ensure_loaded()
        assert self._tokenizer is not None
        assert self._model is not None
        assert self._torch is not None

        encoded = self._tokenizer(
            clean_text,
            return_tensors="pt",
            truncation=True,
            max_length=self.max_length,
            padding=True,
        )
        encoded = {key: value.to(self._device) for key, value in encoded.items()}

        with self._torch.inference_mode():
            logits = self._model(**encoded).logits[0]
            probabilities = self._torch.sigmoid(logits).detach().cpu().tolist()

        raw_scores = dict(zip(self._label_order, probabilities, strict=True))
        scores = {label: round(float(raw_scores[label]), 4) for label in LABELS}
        top_label = max(scores, key=scores.get)
        top_score = scores[top_label]
        flagged = top_score >= self.threshold

        if top_score >= 0.85:
            verdict = "high_risk"
        elif flagged:
            verdict = "review"
        elif top_score >= 0.35:
            verdict = "watch"
        else:
            verdict = "clear"

        return AnalysisResult(
            text=clean_text,
            scores=scores,
            top_label=top_label,
            top_score=top_score,
            verdict=verdict,
            flagged=flagged,
            threshold=self.threshold,
        )
