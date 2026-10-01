from pathlib import Path

import joblib
import pandas as pd

from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    classification_report
)

from xgboost import XGBClassifier


# -----------------------------
# 1. Load dataset
# -----------------------------

DATA_PATH = Path("model/data/transactions.csv")

df = pd.read_csv(DATA_PATH)

print("Dataset loaded successfully!")
print("Total rows:", len(df))


# -----------------------------
# 2. Select AI features
# -----------------------------

FEATURES = [
    "amount",
    "recipient_new",
    "hour",
    "device_changed",
    "location_changed",
    "transactions_last_1h",
    "average_transaction_amount",
    "amount_ratio",
    "account_age_days",
]

TARGET = "fraud_label"

X = df[FEATURES]
y = df[TARGET]


# -----------------------------
# 3. Train / Test split
# -----------------------------

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.20,
    random_state=42,
    stratify=y
)

print("Training rows:", len(X_train))
print("Testing rows:", len(X_test))


# -----------------------------
# 4. Train XGBoost model
# -----------------------------

model = XGBClassifier(
    n_estimators=150,
    max_depth=4,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    eval_metric="logloss",
    random_state=42
)

model.fit(X_train, y_train)

print("\nModel training completed!")


# -----------------------------
# 5. Predictions
# -----------------------------

predictions = model.predict(X_test)


# -----------------------------
# 6. Evaluation
# -----------------------------

accuracy = accuracy_score(y_test, predictions)
precision = precision_score(y_test, predictions)
recall = recall_score(y_test, predictions)
f1 = f1_score(y_test, predictions)

print("\n------ MODEL RESULTS ------")

print(f"Accuracy:  {accuracy:.4f}")
print(f"Precision: {precision:.4f}")
print(f"Recall:    {recall:.4f}")
print(f"F1 Score:  {f1:.4f}")

print("\nConfusion Matrix:")
print(confusion_matrix(y_test, predictions))

print("\nClassification Report:")
print(classification_report(y_test, predictions))


# -----------------------------
# 7. Save trained model
# -----------------------------

MODEL_DIR = Path("model/saved_models")
MODEL_DIR.mkdir(parents=True, exist_ok=True)

MODEL_PATH = MODEL_DIR / "fraud_xgboost.pkl"

joblib.dump(model, MODEL_PATH)


# Save feature names too
FEATURE_PATH = MODEL_DIR / "features.pkl"

joblib.dump(FEATURES, FEATURE_PATH)


print("\nModel saved successfully!")
print("Location:", MODEL_PATH)