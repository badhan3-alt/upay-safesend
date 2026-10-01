from django.db import models

# Create your models here.
from django.db import models


class Transaction(models.Model):
    RISK_LEVELS = [
        ("LOW", "Low"),
        ("MEDIUM", "Medium"),
        ("HIGH", "High"),
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
    risk_level = models.CharField(
        max_length=10,
        choices=RISK_LEVELS,
        default="LOW"
    )

    is_suspicious = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.transaction_id} - {self.amount}"