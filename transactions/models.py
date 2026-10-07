from django.db import models


class Recipient(models.Model):
    recipient_id = models.CharField(max_length=50, primary_key=True)
    is_active = models.BooleanField(default=True, db_index=True)

    def __str__(self):
        return self.recipient_id


class Transaction(models.Model):
    RISK_LEVELS = [
        ("LOW", "Low"),
        ("MEDIUM", "Medium"),
        ("HIGH", "High"),
    ]
    ANALYST_STATUSES = [
        ("PENDING", "Pending"),
        ("REVIEWED", "Reviewed"),
        ("ESCALATED", "Escalated"),
        ("CLEARED", "Cleared"),
    ]

    transaction_id = models.CharField(max_length=50, unique=True)
    user_id = models.CharField(max_length=50)
    recipient_id = models.CharField(max_length=50)

    amount = models.DecimalField(max_digits=12, decimal_places=2)

    recipient_new = models.BooleanField(default=False)
    device_changed = models.BooleanField(default=False)
    location_changed = models.BooleanField(default=False)

    transactions_last_1h = models.IntegerField(default=0)
    average_transaction_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    account_age_days = models.IntegerField(default=0)

    risk_score = models.FloatField(default=0)
    fraud_probability = models.FloatField(default=0)
    anomaly_score = models.FloatField(default=0)
    risk_level = models.CharField(
        max_length=10,
        choices=RISK_LEVELS,
        default="LOW"
    )

    is_suspicious = models.BooleanField(default=False)
    behavioral_anomaly = models.BooleanField(default=False)
    behavioral_features = models.JSONField(default=dict)
    risk_factors = models.JSONField(default=list)
    recommendation = models.JSONField(default=dict)
    analyst_status = models.CharField(
        max_length=10,
        choices=ANALYST_STATUSES,
        default="PENDING",
        db_index=True,
    )
    user_verified = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(
                fields=["user_id", "created_at"],
                name="txn_user_created_idx",
            ),
            models.Index(
                fields=["user_id", "recipient_id", "created_at"],
                name="txn_user_rec_created_idx",
            ),
        ]

    def __str__(self):
        return f"{self.transaction_id} - {self.amount}"