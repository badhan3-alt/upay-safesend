from rest_framework import serializers


class RiskPredictionSerializer(serializers.Serializer):
    amount = serializers.FloatField(min_value=0.01)
    recipient_new = serializers.BooleanField(default=False)
    hour = serializers.IntegerField(min_value=0, max_value=23, default=14)
    device_changed = serializers.BooleanField(default=False)
    location_changed = serializers.BooleanField(default=False)
    transactions_last_1h = serializers.IntegerField(min_value=0, default=1)
    average_transaction_amount = serializers.FloatField(min_value=0.01, default=2500.0)
    account_age_days = serializers.IntegerField(min_value=0, default=180)


class SendMoneySerializer(serializers.Serializer):
    user_id = serializers.CharField(max_length=50, default="U0001")
    recipient_id = serializers.CharField(max_length=50)
    amount = serializers.FloatField(min_value=1.0)
    device_changed = serializers.BooleanField(required=False, default=False)
    location_changed = serializers.BooleanField(required=False, default=False)
    hour = serializers.IntegerField(required=False, min_value=0, max_value=23, default=None)


class ConfirmTransactionSerializer(serializers.Serializer):
    user_id = serializers.CharField(max_length=50, default="U0001")
    recipient_id = serializers.CharField(max_length=50)
    amount = serializers.FloatField(min_value=1.0)
    risk_score = serializers.FloatField(default=0.0)
    risk_level = serializers.CharField(max_length=10, default="LOW")
    recipient_new = serializers.BooleanField(default=False)
    device_changed = serializers.BooleanField(default=False)
    location_changed = serializers.BooleanField(default=False)
    verified_by_user = serializers.BooleanField(default=True)