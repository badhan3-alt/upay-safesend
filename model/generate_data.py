import pandas as pd
import numpy as np
import random
from pathlib import Path

np.random.seed(42)
random.seed(42)

ROWS = 10000

data = []

for i in range(ROWS):
    user_id = f"U{random.randint(1, 800):04d}"
    recipient_id = f"R{random.randint(1, 1500):04d}"

    avg_amount = round(np.random.uniform(300, 5000), 2)

    is_fraud = np.random.choice(
        [0, 1],
        p=[0.92, 0.08]
    )

    if is_fraud:
        amount = round(
            avg_amount * np.random.uniform(3, 12),
            2
        )

        recipient_new = np.random.choice(
            [0, 1],
            p=[0.2, 0.8]
        )

        device_changed = np.random.choice(
            [0, 1],
            p=[0.4, 0.6]
        )

        location_changed = np.random.choice(
            [0, 1],
            p=[0.5, 0.5]
        )

        transactions_last_1h = random.randint(3, 10)

        hour = np.random.choice(
            list(range(24))
        )

    else:
        amount = round(
            avg_amount * np.random.uniform(0.3, 2),
            2
        )

        recipient_new = np.random.choice(
            [0, 1],
            p=[0.8, 0.2]
        )

        device_changed = np.random.choice(
            [0, 1],
            p=[0.95, 0.05]
        )

        location_changed = np.random.choice(
            [0, 1],
            p=[0.95, 0.05]
        )

        transactions_last_1h = random.randint(0, 3)

        hour = np.random.choice(
            list(range(7, 24))
        )

    account_age_days = random.randint(10, 2000)

    amount_ratio = round(
        amount / avg_amount,
        2
    )

    data.append({
        "transaction_id": f"T{i+1:05d}",
        "user_id": user_id,
        "recipient_id": recipient_id,
        "amount": amount,
        "recipient_new": recipient_new,
        "hour": hour,
        "device_changed": device_changed,
        "location_changed": location_changed,
        "transactions_last_1h": transactions_last_1h,
        "average_transaction_amount": avg_amount,
        "amount_ratio": amount_ratio,
        "account_age_days": account_age_days,
        "fraud_label": is_fraud,
    })


df = pd.DataFrame(data)

output_dir = Path("model/data")
output_dir.mkdir(parents=True, exist_ok=True)

output_file = output_dir / "transactions.csv"

df.to_csv(output_file, index=False)

print("Dataset generated successfully.")
print(f"Rows: {len(df)}")
print(f"Fraud transactions: {df['fraud_label'].sum()}")
print(f"Normal transactions: {(df['fraud_label'] == 0).sum()}")
print()
print(df.head())