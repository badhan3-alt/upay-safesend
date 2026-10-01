from pathlib import Path

import joblib
import pandas as pd

from django.conf import settings
from rest_framework import generics, status
from rest_framework.response import Response

from .serializers import RiskPredictionSerializer


# -----------------------------
# Load XGBoost model
# -----------------------------

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

ANOMALY_MODEL_PATH = (
    Path(settings.BASE_DIR)
    / "model"
    / "saved_models"
    / "isolation_forest.pkl"
)


model = joblib.load(MODEL_PATH)
features = joblib.load(FEATURE_PATH)
anomaly_model = joblib.load(ANOMALY_MODEL_PATH)


class RiskPredictionView(generics.GenericAPIView):

    serializer_class = RiskPredictionSerializer

    def post(self, request):

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data

        # -----------------------------
        # Calculate amount ratio
        # -----------------------------

        average_amount = data["average_transaction_amount"]

        if average_amount > 0:
            amount_ratio = data["amount"] / average_amount
        else:
            amount_ratio = 0


        # -----------------------------
        # Prepare transaction data
        # -----------------------------

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


        # -----------------------------
        # XGBoost prediction
        # -----------------------------

        fraud_probability = model.predict_proba(transaction)[0][1]

        xgb_score = float(fraud_probability) * 100


        # -----------------------------
        # Isolation Forest
        # -----------------------------

        anomaly_prediction = anomaly_model.predict(transaction)[0]

        # Isolation Forest:
        # 1  = normal
        # -1 = anomaly

        is_anomaly = anomaly_prediction == -1

        anomaly_score = 100 if is_anomaly else 0


        # -----------------------------
        # Combined risk score
        # -----------------------------

        risk_score = round(
            (0.80 * xgb_score)
            + (0.20 * anomaly_score),
            2
        )


        # -----------------------------
        # Risk level
        # -----------------------------

        if risk_score >= 70:
            risk_level = "HIGH"

        elif risk_score >= 30:
            risk_level = "MEDIUM"

        else:
            risk_level = "LOW"


        # -----------------------------
        # Generate reasons
        # -----------------------------

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

        if is_anomaly:
            reasons.append(
                "Transaction behavior is significantly different from normal patterns"
            )


        # -----------------------------
        # Recommendation
        # -----------------------------

        if risk_level == "HIGH":

            recommendation = (
                "Verify the recipient before continuing."
            )

        elif risk_level == "MEDIUM":

            recommendation = (
                "Review the transaction details carefully."
            )

        else:

            recommendation = (
                "No significant risk detected."
            )


        # -----------------------------
        # API response
        # -----------------------------

        return Response(
            {
                "risk_score": risk_score,
                "risk_level": risk_level,
                "xgboost_score": round(xgb_score, 2),
                "behavioral_anomaly": is_anomaly,
                "reasons": reasons,
                "recommendation": recommendation,
            },
            status=status.HTTP_200_OK,
        )