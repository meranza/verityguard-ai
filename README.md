# VerityGuard AI

VerityGuard is an explainable, multi-label abusive-language screening application. It uses the [`unitary/toxic-bert`](https://huggingface.co/unitary/toxic-bert) checkpoint to return independent probabilities for six Jigsaw toxicity labels:

- `toxic`
- `severe_toxic`
- `obscene`
- `threat`
- `insult`
- `identity_hate`

The interface is designed for human-in-the-loop moderation. A score is evidence for review, not an automatic judgment about intent.

## Why this rebuild exists

The original notebook and Flask demo did not implement the same problem:

- The notebook trained a **single binary output** using only `train["toxic"]`.
- The Flask app expected **six probabilities** from unrelated logistic-regression files.
- Those model files were absent and referenced through a hard-coded Windows path.
- The tokenizer artifact did not match the Flask TF-IDF inference path.
- Templates and an explicit label-to-logit contract were missing.
- Training ran twice, while the second loop never appended losses for its chart.

VerityGuard fixes the core contract. The configured checkpoint must expose six compatible outputs, each logit receives sigmoid independently, and results are returned in a stable canonical order. An incompatible model fails closed instead of producing mislabeled scores.

## Architecture

```text
Browser
  â””â”€ POST /api/analyze
       â””â”€ Flask validation
            â””â”€ ToxicityClassifier
                 â”œâ”€ AutoTokenizer
                 â”œâ”€ AutoModelForSequenceClassification
                 â”œâ”€ six independent sigmoid probabilities
                 â””â”€ canonical label mapping + review verdict
```

The transformer is loaded lazily on the first analysis request. This keeps health checks and process startup responsive. The initial request downloads the model if it is not already cached.

## Run locally

Python 3.11 or 3.12 is recommended.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python run.py
```

On Windows PowerShell, activate the environment with:

```powershell
.venv\Scripts\Activate.ps1
```

Then open [http://127.0.0.1:5000](http://127.0.0.1:5000).

## API

### Analyze text

```http
POST /api/analyze
Content-Type: application/json

{"text": "Text to inspect"}
```

Example response shape:

```json
{
  "flagged": true,
  "scores": {
    "toxic": 0.91,
    "severe_toxic": 0.12,
    "obscene": 0.66,
    "threat": 0.03,
    "insult": 0.82,
    "identity_hate": 0.04
  },
  "threshold": 0.5,
  "top_label": "toxic",
  "top_score": 0.91,
  "verdict": "high_risk"
}
```

### Health check

```http
GET /health
```

The health endpoint reports whether the process is healthy and whether the lazy model has been loaded.

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `MODEL_NAME` | `unitary/toxic-bert` | Hugging Face model identifier |
| `TOXICITY_THRESHOLD` | `0.50` | Threshold that recommends review |
| `HOST` | `127.0.0.1` | Development server host |
| `PORT` | `5000` | HTTP port |
| `FLASK_DEBUG` | `0` | Enable Flask debug mode when set to `1` |

## Test

Tests use an injected deterministic classifier, so CI does not download model weights.

```bash
pip install Flask==3.1.2 pytest==8.4.1
pytest -q
```

The suite checks API validation, all six canonical labels, security headers, model-label compatibility, and health behavior.

## Responsible use

Automated toxicity systems can overreact to profanity, quotations, humor, reclaimed language, and mentions of identity groups. They may reflect bias in their training data. VerityGuard should help moderators prioritize content; it should not autonomously punish users or replace contextual review.

Do not use this project as the sole basis for decisions that affect a person's access, employment, education, housing, credit, or legal rights.

## License

MIT

