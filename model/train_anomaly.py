import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from feature_schema import MODEL_FEATURES


DATA_PATH = Path("model/data/transactions.csv")
MODEL_DIR = Path("model/saved_models")
TARGET = "fraud_label"

df = pd.read_csv(DATA_PATH, parse_dates=["created_at"]).sort_values("created_at")
split_index = int(len(df) * 0.8)
training_data = df.iloc[:split_index]
normal_data = training_data.loc[
    training_data[TARGET] == 0,
    MODEL_FEATURES,
]

model = IsolationForest(
    n_estimators=200,
    contamination=0.05,
    random_state=42,
)
model.fit(normal_data)
normal_decisions = model.decision_function(normal_data)
positive_decisions = normal_decisions[normal_decisions > 0]
if len(positive_decisions) == 0:
    raise ValueError("Isolation Forest produced no normal-side calibration scores.")
anomaly_scale = max(float(np.quantile(positive_decisions, 0.05)), 0.001)

MODEL_DIR.mkdir(parents=True, exist_ok=True)
joblib.dump(model, MODEL_DIR / "isolation_forest.pkl")
(MODEL_DIR / "anomaly_calibration.json").write_text(
    json.dumps({"normal_positive_decision_p05": anomaly_scale}, indent=2) + "\n",
    encoding="utf-8",
)

print(f"Isolation Forest trained on {len(normal_data)} historical normal transfers.")
print(f"Anomaly score calibration scale: {anomaly_scale:.6f}")
print(f"Saved model to {MODEL_DIR / 'isolation_forest.pkl'}")
