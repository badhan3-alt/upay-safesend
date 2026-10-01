from rest_framework import serializers


class RiskPredictionSerializer(serializers.Serializer):
    amount = serializers.FloatField()
    recipient_new = serializers.BooleanField()
    hour = serializers.IntegerField(min_value=0, max_value=23)
    device_changed = serializers.BooleanField()
    location_changed = serializers.BooleanField()
    transactions_last_1h = serializers.IntegerField(min_value=0)
    average_transaction_amount = serializers.FloatField()
    account_age_days = serializers.IntegerField(min_value=0)