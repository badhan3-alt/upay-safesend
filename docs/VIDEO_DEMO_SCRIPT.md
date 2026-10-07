# SafeSend Phase 2 Demo Script (2–3 minutes)

## Before recording

1. Apply migrations and start the server with `DEBUG=True`.
2. Create an analyst user and either set `is_staff` or add the user to the Django group named `Analyst`.
3. Confirm the active recipient directory contains `01711223344` and `01300998877` (both are seeded by migration).
4. Use a fresh demo sender, or note existing history so the repeated-transfer example is easy to follow.
5. Optional: run `python scripts/load_test.py` and show its measured output without describing it as a production capacity test.

## 0:00–0:25 — What SafeSend does

**Show:** Wallet demo at `/`.

**Say:**

> “Upay SafeSend is a prototype that checks a simulated transfer before confirmation. It compares the transaction with persistent sender history, shows separate supervised and anomaly-model outputs, and explains the details that need attention. The current model evaluation uses synthetic data only.”

## 0:25–1:10 — Before vs. after: repeated transfers

**Show:** Send ৳399 to the same active recipient (`01711223344`) from sender `U0001`. Confirm the first two transfers. Keep all three attempts within ten minutes.

**Say:**

> “The first transfer gives SafeSend a baseline. The next attempt is also saved in the database. For the third similar-value attempt, the API finds two matching prior transfers to this recipient within ten minutes. The current attempt is excluded from the historical query, then counted in the explanation as the third transfer.”

**Show:** The warning screen's exact returned reason, fraud probability, anomaly score/status, and recommended action. The displayed result is generated live; do not narrate a fixed score.

**Say:**

> “This is the Phase 2 difference: the behavior is calculated from database rows across requests, not from an in-memory list. The repeat-transfer guardrail is kept distinct from the learned model score.”

## 1:10–1:35 — Transaction context and model outputs

**Show:** Simulator at `/simulator/`. Try an ordinary example, then the late-night high-value preset.

**Say:**

> “The feature vector includes amount relative to the sender's average, transaction velocity, recipient frequency, time since the prior transaction, and recent same-recipient and similar-amount counts. XGBoost provides a fraud probability. Isolation Forest provides a separate anomaly signal; it is not presented as a fraud probability. The customer-facing reasons are based on observed features and triggered rules, not SHAP.”

## 1:35–2:05 — Analyst workflow

**Show:** Sign in at `/analyst/login/` as an authorized analyst, then open `/analyst/`.

**Say:**

> “The analyst dashboard now requires authentication. It shows each stored transaction's risk score, fraud probability, anomaly state, behavioral flags, reasons, recommended action, and review state. The analyst can persist Pending, Reviewed, Escalated, or Cleared.”

**Show:** Change one transaction to Escalated and refresh to show the saved status.

## 2:05–2:30 — Evaluation and limitations

**Show:** `model/saved_models/evaluation_metrics.json` or the evaluation table in the README.

**Say:**

> “The current chronological synthetic holdout reports 76.65% recall, 0.9308 PR-AUC, and a 0.17% false-positive rate. It also missed 60 fraud examples, so this is not a production-performance claim. Real customer impact and loss reduction still need a governed evaluation with Upay data.”

**Close:**

> “Phase 2 adds persistent behavioral history, explicit model-versus-guardrail outputs, human-readable explanations, protected analyst access, and measurable synthetic validation. Redis and production payment integration remain future work.”
