# Upay SafeSend

SafeSend is a Django prototype that screens simulated wallet transfers before confirmation. It combines a supervised fraud probability, a separate Isolation Forest anomaly signal, recent transaction behavior, bilingual explanations, and an analyst review workflow. The included data is synthetic; this project has not been validated on Upay customer data or measured for real-world loss reduction.

## Project overview

- **Problem:** A payment screen gives a customer little context when a transfer resembles scam or account-takeover activity.
- **Prototype response:** Analyze transaction details and database-backed sender history, explain relevant signals, and ask the customer to pause or confirm.
- **Intended users:** Wallet customers in the demo flow and authorized fraud analysts.
- **Deployment demo:** [upay-safesend.onrender.com](https://upay-safesend.onrender.com)

## Features

- Pre-confirmation risk assessment using XGBoost and Isolation Forest.
- Repeated-transfer guardrail for at least three similar-value attempts to one recipient within ten minutes.
- Behavior from persistent transaction history, not a process-local list.
- User-facing reasons, recommended next steps, and English/Bangla text.
- Analyst sign-in, transaction investigation, and persistent Pending / Reviewed / Escalated / Cleared states.
- A seeded, admin-managed prototype recipient directory. Production recipient verification must use Upay's authoritative wallet service.
- CSRF-protected browser submissions, server-side amount and identifier validation, and analyst-only monitoring endpoints.

## Stack

- Python 3.12, Django 6.1, Django REST Framework
- XGBoost, scikit-learn Isolation Forest, pandas, NumPy, joblib
- SQLite by default; PostgreSQL through `DATABASE_URL`
- HTML, CSS, and JavaScript

## Behavioral features

The persisted-history API and training pipeline use the same feature order from [`model/feature_schema.py`](model/feature_schema.py):

| Feature | Meaning |
| --- | --- |
| `amount` | Current transfer amount |
| `amount_ratio` | Amount divided by the sender's prior average |
| `transactions_last_1h` | Sender transactions in the previous hour |
| `total_transactions_10m` | Sender transactions in the previous ten minutes |
| `same_receiver_count_5m` | Sender transfers to this recipient in five minutes |
| `same_receiver_count_10m` | Sender transfers to this recipient in ten minutes |
| `similar_amount_count_10m` | Transfers to this recipient within ±5% of the amount in ten minutes |
| `time_since_last_transaction` | Minutes since the sender's previous transfer |
| `average_transaction_amount` | Historical sender average |
| `recipient_frequency` | Historical transfers from this sender to this recipient |
| `recipient_new` | Whether the sender has used this recipient before |
| `hour` | Transfer hour, 0–23 |
| `device_changed` | Simulated unfamiliar-device signal |
| `location_changed` | Simulated unusual-location signal |
| `account_age_days` | Sender account age used by the synthetic model |

For a new attempt, historical counts exclude the current attempt. The third similar transfer therefore sees two matching confirmed transfers in the preceding ten minutes and triggers the guardrail. Amount similarity is inclusive of five percent above or below the attempted amount.

## Risk decision and explanations

1. XGBoost supplies the fraud probability and primary 0–100 risk score.
2. Isolation Forest supplies a separate anomaly score and flag. The score is a calibrated model signal, **not a fraud probability**.
3. A repeated-similar-transfer guardrail applies a minimum score of 70; it is reported separately from the model outputs.
4. `LOW` is below 30, `MEDIUM` is 30 to below 70, and `HIGH` is 70 or above.

Explanations are generated from measured behavioral features, model outputs, and triggered guardrails. The interface does not claim SHAP or per-instance feature attribution.

## Architecture

```text
Wallet demo
    │ POST + CSRF
    ▼
Django / DRF ── query transaction history ──► Relational database
    │                                         ├─ Sender and recipient velocity
    │                                         ├─ Historical amount baseline
    │                                         └─ Persistent score and review state
    ├─ Behavioral feature vector ──► XGBoost fraud probability
    ├─ Behavioral feature vector ──► Isolation Forest anomaly signal
    ├─ Separate repeated-transfer safety guardrail
    └─ Risk result, reasons, and recommended action

Analyst login ──► protected dashboard and analyst-only monitoring API
```

The prototype uses Django and a relational database. Redis or a separate feature store is intentionally deferred. A production design could place Redis / a feature store between the authenticated Upay transaction API and a separately scaled inference service.

## Model evaluation

The reproducible synthetic dataset has 10,000 chronological rows. Training uses the oldest 8,000; the newest 2,000 are held out. The XGBoost metrics below are calculated at a 0.50 probability threshold. The dataset is generated from injected synthetic patterns and these values are not estimates of production performance.

| Metric | Chronological holdout |
| --- | ---: |
| Accuracy | 96.85% |
| Precision | 98.50% |
| Recall | 76.65% |
| F1 | 86.21% |
| ROC-AUC | 0.9735 |
| PR-AUC (average precision) | 0.9308 |
| False-positive rate | 0.17% |

Confusion matrix (actual rows: normal, fraud; predicted columns: normal, fraud):

```text
                 Predicted normal  Predicted fraud
Actual normal            1740                3
Actual fraud                60              197
```

The 60 false negatives matter: the model does not detect every injected fraud case. Metrics are generated by [`model/train_model.py`](model/train_model.py) and written to `model/saved_models/evaluation_metrics.json`; rerun training after changing the data or features before changing these reported values.

## Setup

Prerequisites: Python 3.12 and Git.

```powershell
git clone https://github.com/badhan3-alt/upay-safesend.git
Set-Location upay-safesend
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
$env:DEBUG = "True"
$env:SECRET_KEY = "set-a-random-local-development-secret"
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open:

- Wallet demo: <http://127.0.0.1:8000/>
- Simulator: <http://127.0.0.1:8000/simulator/>
- Analyst sign-in: <http://127.0.0.1:8000/analyst/login/>
- Django admin: <http://127.0.0.1:8000/admin/>

Use a unique random local `SECRET_KEY`. The application refuses to start outside debug/test mode if `SECRET_KEY` is missing; the Render blueprint generates one. There are no default analyst credentials. Create a user, then either mark it as staff or assign it to a Django group named `Analyst` in the admin.

`Recipient` records are seeded by migration for the demo and can be managed in Django admin. Only active directory entries are accepted by transfer endpoints. This is a mock directory, not a connection to Upay's wallet registry.

## Environment configuration

| Variable | Purpose |
| --- | --- |
| `SECRET_KEY` | Required signing key outside debug/test mode; keep it out of source control |
| `DEBUG` | Set `True` only for local development |
| `ALLOWED_HOSTS` | Optional comma-separated host list |
| `DATABASE_URL` | Optional database URL; defaults to `db.sqlite3` |

## Commands

```powershell
# Apply schema changes
python manage.py migrate

# Run focused tests or the full suite
python manage.py test risk_api dashboard
python manage.py test

# Recreate the synthetic training data and models
python model/generate_data.py
python model/train_model.py
python model/train_anomaly.py

# Check model / schema state
python manage.py check
python manage.py makemigrations --check --dry-run
```

`python manage.py seed_data` is optional demo data only; review that command before using it because it replaces existing transaction rows.

### Load check

Start the local server with `DEBUG=True`, then run:

```powershell
python scripts/load_test.py
```

The standard run sends 100, 500, and 1,000 concurrent CSRF-protected requests to `/api/risk/send-money/` using eight workers. It prints successful requests, errors, average response time, and elapsed wall time for this machine. These are prototype smoke/load measurements, not a production capacity claim.

Observed local run against the Django development server and SQLite, with eight workers:

| Requests | Successful | Errors | Average response | Wall time |
| ---: | ---: | ---: | ---: | ---: |
| 100 | 100 | 0 | 498.11 ms | 6.53 s |
| 500 | 500 | 0 | 461.39 ms | 29.04 s |
| 1,000 | 1,000 | 0 | 602.03 ms | 75.53 s |

These single-run figures depend on the local machine and development configuration. They demonstrate request-path functionality only; they are not production capacity, availability, or latency guarantees.

## API

| Method | Endpoint | Access |
| --- | --- | --- |
| `POST` | `/api/risk/predict/` | CSRF-protected simulator; accepts feature values |
| `POST` | `/api/risk/send-money/` | CSRF-protected demo; derives behavior from database history |
| `POST` | `/api/risk/confirm/` | CSRF-protected demo; recomputes risk on the server and persists the result |
| `GET` | `/api/risk/stats/` | Analyst or staff account |
| `GET` | `/api/transactions/` | Analyst or staff account |

Transfer endpoints reject non-positive / out-of-storage-range amounts, malformed or self-recipient identifiers, and recipients absent from the active prototype directory. The confirmation endpoint ignores client-provided scores and recalculates them from validated data and stored history.

The wallet demo still uses caller-supplied demo sender IDs and does not authenticate real customers. Before any real payment integration, protect customer endpoints with Upay identity/session authentication, obtain sender identity from that authenticated principal, connect recipient checks to the authoritative wallet service, enforce payment authorization/step-up verification, and add production rate limiting and abuse monitoring. Browser POSTs use Django CSRF tokens; analyst pages and APIs require an authenticated analyst or staff account. Django secret values are environment-provided.

## Phase 2 Improvements

- Behavioral repeated-transaction detection and similar-amount velocity detection.
- Expanded history-derived features for XGBoost and Isolation Forest.
- Chronological holdout validation with precision, recall, F1, ROC-AUC, PR-AUC, confusion matrix, and false-positive rate.
- Human-readable, bilingual explanations from behavioral features, model outputs, and safety rules.
- Analyst authentication and persistent Pending / Reviewed / Escalated / Cleared states.
- Persistent transaction history and backend-only risk recomputation on confirmation.
- Recipient input validation, analyst-only monitoring APIs, CSRF protection, and environment-based secrets.
- Reproducible request-volume smoke test and a before-vs-after demo walkthrough.

## Business impact and limitations

Measured now: synthetic-data recall, PR-AUC, false-positive rate, generated high-risk decisions, and whether a user confirmed a transfer in the prototype. Not measured: prevented losses, customer harm reduction, production latency, or improvement on governed Upay data. Validate those future outcomes with a controlled, privacy-governed evaluation before making business-impact claims.

The synthetic generator encodes the patterns the model learns; chronological splitting reduces temporal leakage but does not replace an independent real-world test. The recipient registry, sender IDs, device/location signals, and wallet flow are simulated. The prototype does not provide biometric verification, payment settlement, graph intelligence, or a production-scale feature store.

## Demo and report

- [Before-vs-after video walkthrough](docs/VIDEO_DEMO_SCRIPT.md)
- [Technical project report](docs/PROJECT_REPORT.md)
