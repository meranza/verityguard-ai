from __future__ import annotations

import pytest

from app import create_app
from app.classifier import AnalysisResult


class FakeClassifier:
    model_name = "test/six-label-model"
    is_loaded = True
    threshold = 0.50

    def predict(self, text: str) -> AnalysisResult:
        scores = {
            "toxic": 0.9321,
            "severe_toxic": 0.2034,
            "obscene": 0.7112,
            "threat": 0.0411,
            "insult": 0.8042,
            "identity_hate": 0.0822,
        }
        return AnalysisResult(
            text=" ".join(text.split()),
            scores=scores,
            top_label="toxic",
            top_score=scores["toxic"],
            verdict="high_risk",
            flagged=True,
            threshold=self.threshold,
        )


@pytest.fixture()
def app():
    app = create_app(FakeClassifier())
    app.config.update(TESTING=True)
    return app


@pytest.fixture()
def client(app):
    return app.test_client()
