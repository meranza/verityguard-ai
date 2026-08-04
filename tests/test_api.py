from app.classifier import LABELS


def test_homepage_renders(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Abusive language detection" in response.data
    assert b"Analyze comment" in response.data
    assert b"Label probabilities" in response.data


def test_health_reports_model_state(client):
    payload = client.get("/health").get_json()
    assert payload == {
        "status": "ok",
        "model": "test/six-label-model",
        "model_loaded": True,
    }


def test_analysis_returns_all_six_canonical_labels(client):
    response = client.post("/api/analyze", json={"text": "  Example   comment  "})
    payload = response.get_json()

    assert response.status_code == 200
    assert tuple(payload["scores"].keys()) == LABELS
    assert payload["top_label"] == "toxic"
    assert payload["verdict"] == "high_risk"
    assert payload["flagged"] is True
    assert payload["text"] == "Example comment"


def test_empty_text_is_rejected(client):
    response = client.post("/api/analyze", json={"text": "   "})
    assert response.status_code == 400
    assert response.get_json()["error"] == "Enter a comment to analyze."


def test_non_string_text_is_rejected(client):
    response = client.post("/api/analyze", json={"text": ["not", "text"]})
    assert response.status_code == 400
    assert response.get_json()["error"] == "Text must be a string."


def test_oversized_text_is_rejected(client):
    response = client.post("/api/analyze", json={"text": "x" * 5_001})
    assert response.status_code == 400
    assert "5,000" in response.get_json()["error"]


def test_security_headers_are_present(client):
    response = client.get("/")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
