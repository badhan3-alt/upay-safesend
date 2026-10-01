from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import IsolationForest


DATA_PATH = Path("model/data/transactions.csv")

df = pd.read_csv(DATA_PATH)

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

# Train mainly on normal behaviour
normal_data = df[df["fraud_label"] == 0][FEATURES]

print("Normal transactions used:", len(normal_data))

model = IsolationForest(
    n_estimators=200,
    contamination=0.05,
    random_state=42
)

model.fit(normal_data)

MODEL_DIR = Path("model/saved_models")
MODEL_DIR.mkdir(parents=True, exist_ok=True)

joblib.dump(
    model,
    MODEL_DIR / "isolation_forest.pkl"
)

print("Isolation Forest trained successfully!")
print("Saved to model/saved_models/isolation_forest.pkl")