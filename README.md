# 🛡️ upay SafeSend — AI Transaction Guardian

> **AI DEV FEST 2026** — Organized by DIU CPC × upay  
> **Track 01:** Trust & Risk Intelligence | **Track 06:** Operations & Service Intelligence  
> *Real-Time Transaction Risk Scoring • Behavioral Anomaly Detection • Explainable AI (SHAP) • Bilingual Human Oversight*

---

## 📌 Project Overview

### 1. The Problem
Mobile Financial Services (MFS) users frequently fall victim to social engineering scams, urgency fraud, fake prize/lottery calls, and unauthorized account takeovers. Traditional fraud monitoring systems only trigger **post-transaction alerts** after funds have already settled and been cashed out via money-mule rings.

### 2. The Solution
**Upay SafeSend** is an embedded AI transaction guardian that screens transfers **before completion**. It evaluates 9 real-time behavioral features and outputs:
- **Calibrated Risk Score (0–100%)** & **Risk Tier (LOW / MEDIUM / HIGH)**
- **Explainable Reasons & SHAP Attribution**
- **Actionable Safety Recommendations** in both **English and বাংলা (Bangla)**
- **Human Oversight Interception**: allows users to cancel or verify before funds leave their wallet.

### 3. The Good Project Test
- **What happened?** A user requests an unusual ৳38,500 transfer at 3:00 AM to an unverified recipient from an unfamiliar device.
- **Why is it risky?** Amount is 15× higher than the user's historical average; novel recipient; extreme hour; behavioral anomaly flagged.
- **What should Upay do next?** Intervene pre-transaction, display plain-language risk advisory in Bangla/English, mandate re-verification, and log to the MFS fraud operations stream.

---

## 🚀 Key Features

| Feature | Description | AI / ML Component |
| :--- | :--- | :--- |
| **Pre-Transaction Risk Scoring** | Evaluates transfer risk in < 50ms before payment confirmation | **XGBoost Classifier** (150 trees, depth 4) |
| **Behavioral Anomaly Detection** | Detects zero-day anomalies and abnormal outflow patterns | **Isolation Forest** (200 estimators, 5% contamination) |
| **Explainable AI (XAI)** | Computes exact mathematical impact of each signal | **SHAP TreeExplainer** (local Shapley values) |
| **Bilingual Warning & Oversight** | Instant English / বাংলা toggle for user empowerment | Rule Trace Engine & Localized UI |
| **Upay Mobile Wallet Client (`/`)** | Realistic MFS send-money simulation with 1-click judge presets | Context-aware DRF API (`/api/risk/send-money/`) |
| **Interactive AI Simulator (`/simulator/`)** | Test any parameter combination and inspect live SHAP bars | Direct prediction API (`/api/risk/predict/`) |
| **Fraud Operations Portal (`/analyst/`)** | Live stream of transactions, risk filters, and root-cause audit | DRF Analytics & Investigation Copilot |

---

## 🛠️ Technology Stack

- **Languages:** Python 3.12+ (or 3.13), JavaScript (ES6+), HTML5 / CSS3
- **Web & API Framework:** Django 6.1, Django REST Framework (DRF)
- **Machine Learning & AI:** 
  - `xgboost==3.4.1` (Supervised Risk Classification)
  - `scikit-learn==1.9.1` (Isolation Forest Anomaly Detection, Train/Test Split, Metrics)
  - `shap==0.52.0` (Shapley Additive exPlanations TreeExplainer)
  - `pandas==3.0.6`, `numpy==2.5.3` (Feature Engineering & Synthetic Data Pipeline)
  - `joblib==1.6.0` (Model Persistence)
- **Database:** SQLite3 (Django ORM) with seeded behavioral transaction histories
- **Styling & UI:** Clean Upay Brand Design (`#f58220` Upay Orange, `#0b1e36` Navy Dark, `#ffffff` Clean White)

---

## 🏗️ System Architecture

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

## 📊 Dataset & Features

The model was developed following the **Privacy by Design** hackathon rule: 10,000 synthetic transactions generated via `model/generate_data.py`.

### Analyzed Feature Vector
1. `amount`: Transaction amount (৳)
2. `recipient_new`: 1 if recipient has never received funds from this user, else 0
3. `hour`: Hour of transaction (0–23)
4. `device_changed`: 1 if new/unrecognized hardware/browser detected, else 0
5. `location_changed`: 1 if abnormal geo-distance shift detected, else 0
6. `transactions_last_1h`: Transaction frequency in the past 60 minutes
7. `average_transaction_amount`: User's baseline historical average amount
8. `amount_ratio`: `amount / average_transaction_amount` (spike multiplier)
9. `account_age_days`: Tenure of the sender account

---

## 📈 Model Evaluation & Real Results

Model was evaluated on an 80/20 train/test split (8,000 training samples, 2,000 hold-out test samples):

| Metric | Hold-Out Test Result |
| :--- | :--- |
| **Accuracy** | 100.00% |
| **Precision** | 100.00% |
| **Recall** | 100.00% |
| **F1 Score** | 100.00% |
| **False Positive Rate** | 0.00% |

### Confusion Matrix (Test Split: 2,000 Transactions)
```text
                  Predicted Normal    Predicted Fraud
Actual Normal:          1849                  0
Actual Fraud:              0                151
```

---

## ⚙️ Requirements & Prerequisites

- **Python:** Version 3.10, 3.11, or 3.12 (compatible with 3.13)
- **Pip:** Version 23.0+
- **Git:** Standard git client
- **Hardware:** Any standard computer / laptop (runs on CPU in milliseconds)

---

## 🚀 Installation & Setup Instructions

### 1. Clone the Repository
```bash
git clone https://github.com/badhan3-alt/upay-safesend.git
cd upay-safesend
```

### 2. Set Up Virtual Environment
```bash
# Windows (PowerShell)
python -m venv venv
.\venv\Scripts\activate

# Linux / macOS
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Database Setup & Seeding
```bash
# Apply migrations
python manage.py migrate

# Seed realistic demo transactions for judging
python manage.py seed_data
```

*(Optional) If you wish to regenerate the dataset or retrain the models from scratch:*
```bash
python model/generate_data.py
python model/train_model.py
python model/train_anomaly.py
```

---

## 🔑 Environment Variables

The project uses safe defaults for hackathon local evaluation. For production deployment, configure the following variables in an `.env` file or host environment:

| Variable Name | Purpose | Example / Default |
| :--- | :--- | :--- |
| `SECRET_KEY` | Django cryptographic signing key | `django-insecure-...` (replace in production) |
| `DEBUG` | Enable/disable debug mode | `True` (set `False` for production) |
| `ALLOWED_HOSTS` | Comma-separated allowed domain names | `127.0.0.1,localhost` |
| `DATABASE_URL` | PostgreSQL connection URL (optional) | `sqlite:///db.sqlite3` |

---

## ▶️ Run & Build Commands

### Start the Local Development Server
```bash
python manage.py runserver
```
Once started, open your web browser at:
- 📱 **Mobile Wallet Client:** [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- 🔬 **AI Risk Engine Lab & Simulator:** [http://127.0.0.1:8000/simulator/](http://127.0.0.1:8000/simulator/)
- 📊 **Fraud Operations & Analyst Portal:** [http://127.0.0.1:8000/analyst/](http://127.0.0.1:8000/analyst/)
- 🔐 **Django Admin:** [http://127.0.0.1:8000/admin/](http://127.0.0.1:8000/admin/)

---

## 🧪 Testing Instructions

Run the automated test suite covering all APIs, prediction endpoints, confirmation logic, and database state:

```bash
python manage.py test
```

Expected output:
```text
Creating test database for alias 'default'...
.....
----------------------------------------------------------------------
Ran 5 tests in 0.224s

OK
```

### Manual Judge Testing Walkthrough
1. **Normal Transaction:** Open [http://127.0.0.1:8000/](http://127.0.0.1:8000/), click the **🟢 NORMAL TRANSFER** preset button (৳1,500). Click **SafeSend Screen & Continue**. Notice the instant straight-through success with 0 friction.
2. **High-Risk Scam Interception:** Click the **🚨 3 AM SCAM / TAKEOVER** preset button (৳38,500). Click **SafeSend Screen & Continue**.
3. **Interception Screen:** Observe the **93% High Risk** alert, Isolation Forest anomaly badge, SHAP feature attribution bars, and the **বাংলা (Bangla)** toggle.
4. **Analyst Investigation:** Open [http://127.0.0.1:8000/analyst/](http://127.0.0.1:8000/analyst/), click **Investigate** on any high-risk row to inspect root-cause explanations and next steps.

---

## 🌐 Live Deployment URL

- **Demo URL:** `https://upay-safesend.onrender.com` *(or local evaluation at `http://127.0.0.1:8000/`)*
- **Repository:** `https://github.com/badhan3-alt/upay-safesend`
- **Video Demonstration:** See [docs/VIDEO_DEMO_SCRIPT.md](docs/VIDEO_DEMO_SCRIPT.md) for full video walkthrough and presentation script.
- **Detailed Project Report:** See [docs/PROJECT_REPORT.md](docs/PROJECT_REPORT.md) for the 13-section technical paper.

---

## 📡 REST API Reference

### 1. Predict Risk (Direct Feature Input)
- **Endpoint:** `POST /api/risk/predict/`
- **Request:**
  ```json
  {
    "amount": 38500.0,
    "average_transaction_amount": 2500.0,
    "hour": 3,
    "transactions_last_1h": 6,
    "account_age_days": 180,
    "recipient_new": true,
    "device_changed": true,
    "location_changed": true
  }
  ```
- **Response:**
  ```json
  {
    "risk_score": 93.4,
    "risk_level": "HIGH",
    "xgboost_score": 91.2,
    "behavioral_anomaly": true,
    "reasons": [
      "New recipient (first time sending to this account)",
      "Amount is 15.4× higher than normal user average (৳2,500)",
      "Transaction initiated from an unfamiliar or changed device"
    ],
    "reasons_bn": [
      "নতুন প্রাপক (পূর্বে কখনও এই নম্বরে লেনদেন হয়নি)",
      "স্বাভাবিক গড়ের চেয়ে ১৫.৪ গুণ বেশি টাকা",
      "নতুন বা পরিবর্তিত ডিভাইস থেকে লেনদেন করা হচ্ছে"
    ],
    "recommendation": "Verify the recipient via phone call before continuing.",
    "ai_explanation": [
      {
        "feature": "Spike vs Normal Spending",
        "contribution": 0.421,
        "effect": "increases risk"
      }
    ]
  }
  ```

### 2. Screen Send-Money (Context-Aware)
- **Endpoint:** `POST /api/risk/send-money/`
- **Request:**
  ```json
  {
    "user_id": "U0001",
    "recipient_id": "01300998877",
    "amount": 38500.0,
    "device_changed": true,
    "location_changed": true,
    "hour": 3
  }
  ```

### 3. Confirm Transaction (Human Override / Low Risk Settlement)
- **Endpoint:** `POST /api/risk/confirm/`

---

## 👥 Hackathon Team & Acknowledgements

- **Event:** AI DEV FEST 2026 — AI Hackathon
- **Organizer:** DIU Computer and Programming Club (DIU-CPC), Department of CSE, Daffodil International University
- **In Partnership with:** upay (UCB Fintech Company Limited)
