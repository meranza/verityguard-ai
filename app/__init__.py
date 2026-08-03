"""Flask application factory for VerityGuard."""

from __future__ import annotations

import os
from typing import Any

from flask import Flask, jsonify, render_template, request

from .classifier import ClassifierUnavailable, LABEL_COPY, MODEL_NAME, ToxicityClassifier


MAX_TEXT_LENGTH = 5_000


def create_app(classifier: Any | None = None) -> Flask:
    app = Flask(__name__)
    app.config.update(
        JSON_SORT_KEYS=False,
        MAX_CONTENT_LENGTH=32 * 1024,
        MODEL_NAME=MODEL_NAME,
    )
    app.json.sort_keys = False
    app.config.from_prefixed_env("VERITYGUARD")

    active_classifier = classifier or ToxicityClassifier(
        model_name=app.config["MODEL_NAME"],
        threshold=float(os.getenv("TOXICITY_THRESHOLD", "0.50")),
    )
    app.extensions["toxicity_classifier"] = active_classifier

    @app.after_request
    def add_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        return response

    @app.get("/")
    def index():
        return render_template(
            "index.html",
            labels=LABEL_COPY,
            model_name=app.config["MODEL_NAME"],
            max_text_length=MAX_TEXT_LENGTH,
        )

    @app.post("/api/analyze")
    def analyze():
        payload = request.get_json(silent=True) or {}
        text = payload.get("text", "")

        if not isinstance(text, str):
            return jsonify(error="Text must be a string."), 400
        if not text.strip():
            return jsonify(error="Enter a comment to analyze."), 400
        if len(text) > MAX_TEXT_LENGTH:
            return jsonify(error=f"Text must be {MAX_TEXT_LENGTH:,} characters or fewer."), 400

        try:
            result = active_classifier.predict(text)
        except ValueError as exc:
            return jsonify(error=str(exc)), 400
        except ClassifierUnavailable:
            app.logger.exception("Classifier initialization failed")
            return (
                jsonify(
                    error="The analysis model is temporarily unavailable.",
                    hint="Confirm model dependencies and network access, then retry.",
                ),
                503,
            )

        response = jsonify(result.to_dict())
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/health")
    def health():
        return jsonify(
            status="ok",
            model=active_classifier.model_name,
            model_loaded=active_classifier.is_loaded,
        )

    return app
