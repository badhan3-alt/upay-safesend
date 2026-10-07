from decimal import Decimal

from rest_framework import serializers

from transactions.models import Recipient


class RiskPredictionSerializer(serializers.Serializer):
    amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0.01"),
    )
    recipient_new = serializers.BooleanField(default=False)
    hour = serializers.IntegerField(min_value=0, max_value=23, default=14)
    device_changed = serializers.BooleanField(default=False)
    location_changed = serializers.BooleanField(default=False)
    transactions_last_1h = serializers.IntegerField(min_value=0, default=1)
    average_transaction_amount = serializers.FloatField(min_value=0.01, default=2500.0)
    account_age_days = serializers.IntegerField(min_value=0, default=180)
    total_transactions_10m = serializers.IntegerField(min_value=0, default=0)
    same_receiver_count_5m = serializers.IntegerField(min_value=0, default=0)
    same_receiver_count_10m = serializers.IntegerField(min_value=0, default=0)
    similar_amount_count_10m = serializers.IntegerField(min_value=0, default=0)
    time_since_last_transaction = serializers.FloatField(min_value=0, default=1440)
    recipient_frequency = serializers.IntegerField(min_value=0, default=0)


class TransferSerializer(serializers.Serializer):
    user_id = serializers.RegexField(
        regex=r"^[A-Za-z0-9+_-]+$",
        max_length=50,
        default="U0001",
    )
    recipient_id = serializers.RegexField(
        regex=r"^[A-Za-z0-9+_-]+$",
        max_length=50,
    )
    amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0.01"),
    )

    def validate_recipient_id(self, value):
        if not Recipient.objects.filter(recipient_id=value, is_active=True).exists():
            raise serializers.ValidationError("Recipient is not in the active wallet directory.")
        return value

    def validate(self, attrs):
        if attrs["user_id"] == attrs["recipient_id"]:
            raise serializers.ValidationError(
                {"recipient_id": "Sender and recipient must be different."}
            )
        return attrs


class SendMoneySerializer(TransferSerializer):
    device_changed = serializers.BooleanField(required=False, default=False)
    location_changed = serializers.BooleanField(required=False, default=False)
    hour = serializers.IntegerField(required=False, min_value=0, max_value=23, default=None)


class ConfirmTransactionSerializer(TransferSerializer):
    device_changed = serializers.BooleanField(default=False)
    location_changed = serializers.BooleanField(default=False)
    hour = serializers.IntegerField(required=False, min_value=0, max_value=23, default=None)
    verified_by_user = serializers.BooleanField(default=True)

    def validate_verified_by_user(self, value):
        if not value:
            raise serializers.ValidationError(
                "User confirmation is required before recording a transfer."
            )
        return value