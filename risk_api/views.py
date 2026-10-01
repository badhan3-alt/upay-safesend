from django.shortcuts import render

# Create your views here.
from pathlib import Path

import joblib
import pandas as pd

from django.conf import settings
from rest_framework import generics, status
from rest_framework.response import Response

from .serializers import RiskPredictionSerializer


MODEL_PATH = (
    Path(settings.BASE_DIR)
    / "model"
    / "saved_models"
    / "fraud_xgboost.pkl"
)

FEATURE_PATH = (
    Path(settings.BASE_DIR)
    / "model"
    / "saved_models"
    / "features.pkl"
)

model = joblib.load(MODEL_PATH)
features = joblib.load(FEATURE_PATH)


class RiskPredictionView(generics.GenericAPIView):
    serializer_class = RiskPredictionSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data

        average_amount = data["average_transaction_amount"]

        if average_amount > 0:
            amount_ratio = data["amount"] / average_amount
        else:
            amount_ratio = 0

        transaction = pd.DataFrame([
            {
                "amount": data["amount"],
                "recipient_new": int(data["recipient_new"]),
                "hour": data["hour"],
                "device_changed": int(data["device_changed"]),
                "location_changed": int(data["location_changed"]),
                "transactions_last_1h": data["transactions_last_1h"],
                "average_transaction_amount": average_amount,
                "amount_ratio": amount_ratio,
                "account_age_days": data["account_age_days"],
            }
        ])

        transaction = transaction[features]

        fraud_probability = model.predict_proba(transaction)[0][1]

        risk_score = round(float(fraud_probability) * 100, 2)

        if risk_score >= 70:
            risk_level = "HIGH"
        elif risk_score >= 30:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        reasons = []

        if data["recipient_new"]:
            reasons.append("New recipient")

        if amount_ratio >= 3:
            reasons.append("Amount much higher than normal")

        if data["device_changed"]:
            reasons.append("Device recently changed")

        if data["location_changed"]:
            reasons.append("Location recently changed")

        if data["transactions_last_1h"] >= 4:
            reasons.append("High transaction frequency")

        if data["hour"] <= 5:
            reasons.append("Transaction at unusual time")

        if risk_level == "HIGH":
            recommendation = "Verify the recipient before continuing."
        elif risk_level == "MEDIUM":
            recommendation = "Review the transaction details carefully."
        else:
            recommendation = "No significant risk detected."

        return Response(
            {
                "risk_score": risk_score,
                "risk_level": risk_level,
                "reasons": reasons,
                "recommendation": recommendation,
            },
            status=status.HTTP_200_OK,
        )