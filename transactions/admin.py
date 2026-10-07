from django.contrib import admin

from .models import Recipient, Transaction


@admin.register(Recipient)
class RecipientAdmin(admin.ModelAdmin):
    list_display = ("recipient_id", "is_active")
    list_filter = ("is_active",)
    search_fields = ("recipient_id",)


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = (
        "transaction_id",
        "user_id",
        "recipient_id",
        "amount",
        "risk_level",
        "fraud_probability",
        "behavioral_anomaly",
        "analyst_status",
        "created_at",
    )
    list_filter = ("risk_level", "behavioral_anomaly", "analyst_status")
    search_fields = ("transaction_id", "user_id", "recipient_id")