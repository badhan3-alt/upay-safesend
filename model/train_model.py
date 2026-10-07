import json
from pathlib import Path

import joblib
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from xgboost import XGBClassifier

from feature_schema import MODEL_FEATURES


DATA_PATH = Path("model/data/transactions.csv")
MODEL_DIR = Path("model/saved_models")
TARGET = "fraud_label"

df = pd.read_csv(DATA_PATH, parse_dates=["created_at"]).sort_values("created_at")
split_index = int(len(df) * 0.8)
train_df = df.iloc[:split_index]
test_df = df.iloc[split_index:]

X_train = train_df[MODEL_FEATURES]
y_train = train_df[TARGET]
X_test = test_df[MODEL_FEATURES]
y_test = test_df[TARGET]

model = XGBClassifier(
    n_estimators=150,
    max_depth=4,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    eval_metric="logloss",
    random_state=42,
)
model.fit(X_train, y_train)

probabilities = model.predict_proba(X_test)[:, 1]
predictions = (probabilities >= 0.5).astype(int)
tn, fp, fn, tp = confusion_matrix(y_test, predictions, labels=[0, 1]).ravel()

metrics = {
    "evaluation": "chronological_holdout",
    "training_rows": len(train_df),
    "testing_rows": len(test_df),
    "training_start": train_df["created_at"].min().isoformat(),
    "training_end": train_df["created_at"].max().isoformat(),
    "testing_start": test_df["created_at"].min().isoformat(),
    "testing_end": test_df["created_at"].max().isoformat(),
    "fraud_prevalence": float(y_test.mean()),
    "threshold": 0.5,
    "accuracy": float(accuracy_score(y_test, predictions)),
    "precision": float(precision_score(y_test, predictions, zero_division=0)),
    "recall": float(recall_score(y_test, predictions, zero_division=0)),
    "f1": float(f1_score(y_test, predictions, zero_division=0)),
    "roc_auc": float(roc_auc_score(y_test, probabilities)),
    "pr_auc": float(average_precision_score(y_test, probabilities)),
    "false_positive_rate": float(fp / (fp + tn)) if (fp + tn) else 0.0,
    "confusion_matrix": [[int(tn), int(fp)], [int(fn), int(tp)]],
}

MODEL_DIR.mkdir(parents=True, exist_ok=True)
joblib.dump(model, MODEL_DIR / "fraud_xgboost.pkl")
joblib.dump(MODEL_FEATURES, MODEL_DIR / "features.pkl")
(MODEL_DIR / "evaluation_metrics.json").write_text(
    json.dumps(metrics, indent=2) + "\n",
    encoding="utf-8",
)

print(json.dumps(metrics, indent=2))
print(f"Saved model and evaluation metrics under {MODEL_DIR}")
