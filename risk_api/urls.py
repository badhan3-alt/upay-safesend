from django.urls import path
from .views import (
    ConfirmTransactionView,
    RiskPredictionView,
    SendMoneyRiskView,
    TransactionStatsView,
)

urlpatterns = [
    path("predict/", RiskPredictionView.as_view(), name="predict-risk"),
    path("send-money/", SendMoneyRiskView.as_view(), name="send-money-risk"),
    path("confirm/", ConfirmTransactionView.as_view(), name="confirm-transaction"),
    path("stats/", TransactionStatsView.as_view(), name="transaction-stats"),
]