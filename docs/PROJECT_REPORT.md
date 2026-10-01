# AI DEV FEST 2026 — DIU CPC × upay
## Track 01: Trust & Risk Intelligence / Track 06: Operations & Service Intelligence
# Project Report: Upay SafeSend — AI Transaction Guardian

---

## 1. Introduction

Mobile Financial Services (MFS) have revolutionized financial inclusion across Bangladesh, serving over 120 million registered accounts. As cashless micro-transactions, merchant payments, and peer-to-peer (P2P) transfers become ubiquitous, digital scams and social engineering fraud have surged proportionally. In conventional MFS architectures, fraud management functions retrospectively: transactions settle instantaneously, and fraud detection flags unauthorized movements hours or days later—often after the victim’s money has already been cashed out via intermediary mule accounts.

**Upay SafeSend** fundamentally re-engineers this dynamic by introducing a **pre-transaction behavioral intervention layer**. Powered by an ensemble of supervised learning (XGBoost), unsupervised anomaly detection (Isolation Forest), and explainable AI (SHAP), SafeSend computes a multi-dimensional risk score before funds are irreversibly transferred. If high or unusual risk is detected, SafeSend intervenes with plain-language, bilingual (English & Bangla) explanations and actionable recommendations, providing human oversight that empowers customers to halt fraudulent transactions.

---

## 2. Problem Statement

### 2.1 The Challenge
Every day, Bangladeshi mobile wallet customers face social engineering scams (e.g., lottery scams, fake prize calls, impersonation of family members or law enforcement, and unauthorized account takeovers). Victims are manipulated into completing urgent P2P send-money or cash-out transfers.

### 2.2 Core Friction Points
1. **Irreversibility of MFS Transfers:** Once confirmed via PIN, transfers settle in seconds with no recall mechanism.
2. **Victim Blindness:** Scammers create artificial urgency; victims lack independent warning signals at the moment of transfer.
3. **Black-Box Confusion:** Traditional rule-based alerts are either too opaque ("Transaction blocked - Error 403") or produce high false positives that annoy legitimate users.
4. **Mule Wallet Dispersion:** Scammers funnel stolen funds through networks of newly created or dormant accounts.

### 2.3 The Hackathon Good Project Test
- **What happened?** A user requests a high-value transfer (e.g., ৳38,500) to an unverified recipient at an unusual hour (3:00 AM) from a new device.
- **Why is it risky?** The transfer is 15× higher than the user's habitual average, sent to a first-time recipient, and triggers high anomaly scores across multiple behavioral dimensions.
- **What should Upay do next?** Intervene pre-transaction, present plain-language explanations in Bangla/English, require biometric or cooling-off verification, and log the incident to the MFS Fraud Operations Console.

---

## 3. Proposed Solution: Upay SafeSend

Upay SafeSend operates as an embedded intelligence guardian within the Upay digital wallet.

1. **Pre-Transaction Screening:** Evaluates 9 real-time behavioral features as soon as the customer taps "Continue".
2. **Dual-Engine AI Ensemble:** 
   - **XGBoost Classifier:** Detects known fraud, scam, and takeover patterns.
   - **Isolation Forest:** Catches zero-day, out-of-distribution behavioral anomalies without requiring prior fraud labels.
3. **Local Explainability (SHAP):** Translates complex tree decisions into transparent feature contributions ("Why was this flagged?").
4. **Bilingual Human Oversight:** Displays localized Bengali (বাংলা) and English warnings tailored for Bangladesh's diverse demographic.
5. **Analyst Investigation Copilot:** An operational dashboard enabling MFS risk officers to audit flagged transactions, trace mule networks, and inspect AI decisions.

---

## 4. System Architecture

SafeSend follows a decoupled **Input → Intelligence → Action** architectural pattern:

```text
  [ Upay Mobile Client ] <==== (JSON / REST API) ====> [ Django / DRF Backend ]
          │                                                       │
          ├─ Enter Recipient & Amount                             ├─ Context Assembly (Avg Amount, Velocity)
          ├─ 1-Click Scenarios                                   ├─ Feature Alignment Pipeline
          └─ Bilingual Interception Modal                         │
                                                                  ▼
                                                      [ ML Risk Scoring Engine ]
                                                                  │
                                      ┌───────────────────────────┴───────────────────────────┐
                                      ▼                                                       ▼
                            [ XGBoost Classifier ]                                 [ Isolation Forest ]
                            (Supervised Fraud Prob)                                (Unsupervised Anomaly)
                                      │                                                       │
                                      └───────────────────────────┬───────────────────────────┘
                                                                  ▼
                                                      [ Ensemble Calibrator ]
                                                      Score = 0.75*XGB + 0.25*IF
                                                                  │
                                                                  ▼
                                                      [ SHAP TreeExplainer ]
                                                      (Feature Attribution & Impact)
                                                                  │
                                                                  ▼
                                                      [ Response Payload ]
                                                      • Risk Score & Level (LOW/MED/HIGH)
                                                      • Bilingual Explanations (EN / BN)
                                                      • Actionable Recommendations
                                                      • Investigation Narrative (3 Questions)
```

---

## 5. Synthetic Dataset Strategy

Per the hackathon guidelines (Section 11: "Privacy by Design"), zero production customer data was used. A realistic synthetic dataset of **10,000 transactions** was engineered with reproducible random seeding (`np.random.seed(42)`).

### Dataset Schema (`transactions.csv`)
| Feature | Type | Range / Values | Description |
| :--- | :--- | :--- | :--- |
| `transaction_id` | String | `T00001` - `T10000` | Unique transaction identifier |
| `user_id` | String | `U0001` - `U0800` | Customer account identifier |
| `recipient_id` | String | `R0001` - `R1500` | Counterparty wallet identifier |
| `amount` | Float | ৳90 - ৳60,000 | Current transaction amount |
| `recipient_new` | Binary | `0` or `1` | First-time transaction to this recipient |
| `hour` | Integer | `0` - `23` | Hour of the day in 24h format |
| `device_changed` | Binary | `0` or `1` | Flag for unfamiliar hardware or browser |
| `location_changed` | Binary | `0` or `1` | Flag for unusual IP/GPS deviation |
| `transactions_last_1h` | Integer | `0` - `10` | Frequency / velocity within last 60 minutes |
| `average_transaction_amount` | Float | ৳300 - ৳5,000 | Historical average transaction baseline |
| `amount_ratio` | Float | `amount / avg_amount` | Multiplier relative to normal spending habit |
| `account_age_days` | Integer | `10` - `2000` | Account tenure in days |
| `fraud_label` | Binary | `0` (Normal) or `1` (Fraud) | Ground truth target (8% fraud prevalence) |

---

## 6. AI Models & Methodology

### 6.1 Supervised Model: XGBoost Classifier
- **Algorithm:** Extreme Gradient Boosting (`XGBClassifier`) with depth 4, 150 estimators, learning rate 0.05, and log-loss objective.
- **Role:** Learn non-linear feature interactions that characterize scam transfers (e.g., high `amount_ratio` combined with `recipient_new=1` and `device_changed=1`).

### 6.2 Unsupervised Model: Isolation Forest
- **Algorithm:** `IsolationForest(n_estimators=200, contamination=0.05)`
- **Role:** Trained solely on normal transactions (`fraud_label == 0`). It isolates zero-day anomalies and behavioral shifts that fall outside the customer’s habitual envelope.

### 6.3 Ensemble Calibration
```python
blended_score = (0.75 * xgb_score) + (0.25 * anomaly_score)
risk_score = round(max(0.0, min(100.0, blended_score)), 1)
```
- **Risk Tiers:**
  - `0.0% – 29.9%`: **LOW RISK** (Seamless straight-through processing)
  - `30.0% – 69.9%`: **MEDIUM RISK** (Soft advisory & recipient double-check)
  - `70.0% – 100.0%`: **HIGH RISK** (Active intervention, explanation modal, re-authentication)

### 6.4 Explainable AI: SHAP TreeExplainer
- Uses Shapley Additive exPlanations (`shap.TreeExplainer`) to compute the exact marginal contribution of each feature for the specific transaction.
- Returns top 5 drivers indicating whether each signal increased or reduced overall risk.

---

## 7. System Features

1. **Simulated Mobile Wallet Client (`/`):**
   - Realistic Upay user experience with dynamic balance updates.
   - 1-click preset scenarios for demonstration to judges.
   - Dual-language toggle (English / বাংলা).
2. **Risk Interception & Warning Screen (`/warning/`):**
   - High-impact visual risk gauge and anomaly indicator.
   - Clear rule-based reasons and SHAP attribution bars.
   - Full human-in-the-loop control (`[ Cancel ]` or `[ Verify & Complete ]`).
3. **AI Risk Engine Lab & Simulator (`/simulator/`):**
   - Interactive parameter tuning (Amount, Hour, Velocity, Account Age, Device).
   - Real-time model inference and live SHAP bar visualization.
   - Answers to the 3 hackathon questions.
4. **Fraud Operations & Analyst Portal (`/analyst/`):**
   - Real-time transaction stream with risk filters (`HIGH`, `MEDIUM`, `LOW`).
   - Search across User ID, Recipient, or Transaction ID.
   - Interactive investigation modal summarizing root causes and next steps.

---

## 8. Model Evaluation

Trained on 8,000 synthetic transactions; validated on 2,000 hold-out test transactions:

| Metric | Hold-Out Test Score |
| :--- | :--- |
| **Accuracy** | 100.00% |
| **Precision** | 100.00% |
| **Recall** | 100.00% |
| **F1 Score** | 100.00% |
| **ROC AUC** | 1.0000 |

### Confusion Matrix (Test Split: 2,000 Samples)
- True Normal (TN): 1,849
- False Normal / False Negative (FN): 0
- True Fraud (TP): 151
- False Positive (FP): 0

*Note: In synthetic benchmark distributions where injected fraud patterns have distinct multivariate boundaries, tree ensembles achieve near-perfect separation. When moving to production with noisy real-world data, the dual XGBoost + Isolation Forest architecture maintains resilience against adversarial drift.*

---

## 9. Real-Life Impact & Business Value

1. **Scam Prevention:** Prevents irreversible losses before funds leave the victim's wallet.
2. **Customer Trust:** Customers gain confidence knowing that Upay actively protects their hard-earned money.
3. **Reduced Dispute & Legal Costs:** Intercepting scams pre-transaction drastically reduces call center dispute volume and police/BFIU complaints.
4. **Calibrated Friction:** Safe transactions (92%+) face zero additional friction, while risky transfers receive proportional safety checks.

---

## 10. Responsible AI & Safety

- **Privacy by Design:** Operates exclusively on behavioral metadata and ratios without storing or leaking sensitive PII.
- **Transparency & Explainability:** SHAP attribution ensures decisions are never a black box.
- **Human Oversight:** The AI never unilaterally locks or denies a customer's funds without human recourse; it advises and empowers the user.
- **Bilingual Inclusivity:** Ensures rural and non-English-speaking users have equal access to security insights.

---

## 11. Limitations

1. Relies on synthetic behavioral distributions during prototype stage.
2. Cold-start accounts with fewer than 3 transactions require conservative default baselines.
3. Does not yet analyze device biometric telemetry (e.g. gyroscope or typing cadence).

---

## 12. Future Roadmap

1. **Graph Neural Networks (GNN):** Transaction graph analysis to map money-mule rings across multiple hops.
2. **USSD & SMS Voice Alerts:** Bangla voice synthesis for feature-phone users dialing `*268#`.
3. **Federated Learning:** Cross-institutional scam intelligence sharing in compliance with Bangladesh Bank guidelines.

---

## 13. Conclusion

Upay SafeSend transforms mobile financial protection from passive post-mortem tracking into **active, explainable, and compassionate pre-transaction guardianship**. By merging XGBoost, Isolation Forest, and SHAP within an intuitive bilingual interface, SafeSend proves that advanced AI can directly protect millions of digital wallet users across Bangladesh.
