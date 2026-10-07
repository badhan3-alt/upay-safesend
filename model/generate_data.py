from datetime import datetime, timedelta, timezone
from pathlib import Path
import random

import numpy as np
import pandas as pd

from feature_schema import MODEL_FEATURES


np.random.seed(42)
random.seed(42)

ROWS = 10000
START_TIME = datetime(2026, 1, 1, 7, tzinfo=timezone.utc)

data = []
user_history = {}
account_ages = {}
repeat_remaining = 0
repeat_context = None

for index in range(ROWS):
    timestamp = START_TIME + timedelta(minutes=index)

    if repeat_remaining:
        user_id, recipient_id, repeated_amount = repeat_context
        amount = round(repeated_amount, 2)
        is_fraud = 1
        repeat_remaining -= 1
    elif random.random() < 0.01:
        user_id = f"U{random.randint(1, 200):04d}"
        recipient_id = f"R{random.randint(1, 500):04d}"
        avg_amount = round(np.random.uniform(300, 5000), 2)
        repeated_amount = round(avg_amount * np.random.uniform(0.5, 2.0), 2)
        repeat_context = (user_id, recipient_id, repeated_amount)
        amount = repeated_amount
        is_fraud = 1
        repeat_remaining = 2
    else:
        user_id = f"U{random.randint(1, 200):04d}"
        recipient_id = f"R{random.randint(1, 500):04d}"
        is_fraud = int(np.random.random() < 0.08)
        avg_amount = round(np.random.uniform(300, 5000), 2)
        amount = round(
            avg_amount * np.random.uniform(3, 12)
            if is_fraud
            else avg_amount * np.random.uniform(0.3, 2),
            2,
        )

    history = user_history.setdefault(user_id, [])
    if not history:
        account_ages[user_id] = random.randint(10, 2000)

    recent_10m = [
        row for row in history
        if (timestamp - row["created_at"]).total_seconds() <= 10 * 60
    ]
    recent_5m = [
        row for row in history
        if (timestamp - row["created_at"]).total_seconds() <= 5 * 60
    ]
    same_recipient_10m = [
        row for row in recent_10m if row["recipient_id"] == recipient_id
    ]
    same_recipient_5m = [
        row for row in recent_5m if row["recipient_id"] == recipient_id
    ]
    lower_amount = amount * 0.95
    upper_amount = amount * 1.05
    similar_amount_count_10m = sum(
        lower_amount <= row["amount"] <= upper_amount
        for row in same_recipient_10m
    )
    recipient_frequency = sum(
        row["recipient_id"] == recipient_id for row in history
    )
    average_amount = (
        float(np.mean([row["amount"] for row in history[-50:]]))
        if history
        else avg_amount
    )
    time_since_last = (
        (timestamp - history[-1]["created_at"]).total_seconds() / 60
        if history
        else 1440.0
    )

    amount_ratio = round(amount / max(average_amount, 0.01), 2)
    recipient_new = int(recipient_frequency == 0)
    device_changed = int(
        np.random.choice([0, 1], p=[0.4, 0.6] if is_fraud else [0.95, 0.05])
    )
    location_changed = int(
        np.random.choice([0, 1], p=[0.5, 0.5] if is_fraud else [0.95, 0.05])
    )

    row = {
        "transaction_id": f"T{index + 1:05d}",
        "created_at": timestamp.isoformat(),
        "user_id": user_id,
        "recipient_id": recipient_id,
        "amount": amount,
        "recipient_new": recipient_new,
        "hour": timestamp.hour,
        "device_changed": device_changed,
        "location_changed": location_changed,
        "transactions_last_1h": sum(
            (timestamp - item["created_at"]).total_seconds() <= 60 * 60
            for item in history
        ),
        "average_transaction_amount": round(average_amount, 2),
        "amount_ratio": amount_ratio,
        "account_age_days": account_ages[user_id],
        "total_transactions_10m": len(recent_10m),
        "same_receiver_count_5m": len(same_recipient_5m),
        "same_receiver_count_10m": len(same_recipient_10m),
        "similar_amount_count_10m": similar_amount_count_10m,
        "time_since_last_transaction": round(time_since_last, 2),
        "recipient_frequency": recipient_frequency,
        "fraud_label": is_fraud,
    }
    data.append(row)
    history.append(
        {
            "created_at": timestamp,
            "recipient_id": recipient_id,
            "amount": amount,
        }
    )

df = pd.DataFrame(data)
df = df[["transaction_id", "created_at", "user_id", "recipient_id"] + MODEL_FEATURES + ["fraud_label"]]

output_dir = Path("model/data")
output_dir.mkdir(parents=True, exist_ok=True)
output_file = output_dir / "transactions.csv"
df.to_csv(output_file, index=False)

print("Chronological synthetic dataset generated.")
print(f"Rows: {len(df)}")
print(f"Fraud transactions: {df['fraud_label'].sum()}")
print(f"Normal transactions: {(df['fraud_label'] == 0).sum()}")
print(f"Output: {output_file}")
