from pathlib import Path

import joblib
import pandas as pd
import shap
from rest_framework.permissions import AllowAny
from django.conf import settings
from rest_framework import generics, status
from rest_framework.response import Response

from .serializers import RiskPredictionSerializer


# ============================================================
# MODEL PATHS
# ============================================================

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


# ============================================================
# LOAD MODELS
# ============================================================

model = joblib.load(MODEL_PATH)

features = joblib.load(FEATURE_PATH)

anomaly_model = joblib.load(
    ANOMALY_MODEL_PATH
)


# ============================================================
# SHAP EXPLAINER
# ============================================================

explainer = shap.TreeExplainer(model)


# Friendly names for frontend
FEATURE_NAMES = {
    "amount": "Transaction amount",
    "recipient_new": "New recipient",
    "hour": "Transaction time",
    "device_changed": "Device change",
    "location_changed": "Location change",
    "transactions_last_1h": "Transaction frequency",
    "average_transaction_amount": "Average transaction amount",
    "amount_ratio": "Amount compared with normal",
    "account_age_days": "Account age",
}


# ============================================================
# RISK PREDICTION API
# ============================================================

class RiskPredictionView(generics.GenericAPIView):
    serializer_class = RiskPredictionSerializer
    authentication_classes = []
    permission_classes = [AllowAny]

    serializer_class = RiskPredictionSerializer

    def post(self, request):

        # ----------------------------------------------------
        # Validate input
        # ----------------------------------------------------

        serializer = self.get_serializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        data = serializer.validated_data


        # ----------------------------------------------------
        # Calculate amount ratio
        # ----------------------------------------------------

        average_amount = data[
            "average_transaction_amount"
        ]

        if average_amount > 0:

            amount_ratio = (
                data["amount"]
                / average_amount
            )

        else:

            amount_ratio = 0


        # ----------------------------------------------------
        # Prepare transaction
        # ----------------------------------------------------

        transaction = pd.DataFrame(
            [
                {
                    "amount": data["amount"],

                    "recipient_new":
                        int(data["recipient_new"]),

                    "hour":
                        data["hour"],

                    "device_changed":
                        int(data["device_changed"]),

                    "location_changed":
                        int(data["location_changed"]),

                    "transactions_last_1h":
                        data["transactions_last_1h"],

                    "average_transaction_amount":
                        average_amount,

                    "amount_ratio":
                        amount_ratio,

                    "account_age_days":
                        data["account_age_days"],
                }
            ]
        )

        # Keep feature order exactly
        # the same as training

        transaction = transaction[features]


        # ====================================================
        # 1. XGBOOST PREDICTION
        # ====================================================

        fraud_probability = (
            model.predict_proba(
                transaction
            )[0][1]
        )

        xgb_score = (
            float(fraud_probability)
            * 100
        )


        # ====================================================
        # 2. ISOLATION FOREST
        # ====================================================

        anomaly_prediction = (
            anomaly_model.predict(
                transaction
            )[0]
        )

        # Isolation Forest:
        # 1  = Normal
        # -1 = Anomaly

        is_anomaly = (
            anomaly_prediction == -1
        )

        anomaly_score = (
            100 if is_anomaly else 0
        )


        # ====================================================
        # 3. COMBINED RISK SCORE
        # ====================================================

        risk_score = round(
            (0.80 * xgb_score)
            +
            (0.20 * anomaly_score),
            2
        )


        # ====================================================
        # 4. RISK LEVEL
        # ====================================================

        if risk_score >= 70:

            risk_level = "HIGH"

        elif risk_score >= 30:

            risk_level = "MEDIUM"

        else:

            risk_level = "LOW"


        # ====================================================
        # 5. RULE-BASED REASONS
        # ====================================================

        reasons = []

        if data["recipient_new"]:

            reasons.append(
                "New recipient"
            )

        if amount_ratio >= 3:

            reasons.append(
                "Amount much higher than normal"
            )

        if data["device_changed"]:

            reasons.append(
                "Device recently changed"
            )

        if data["location_changed"]:

            reasons.append(
                "Location recently changed"
            )

        if (
            data["transactions_last_1h"]
            >= 4
        ):

            reasons.append(
                "High transaction frequency"
            )

        if (
            data["hour"] <= 5
            or data["hour"] >= 23
        ):

            reasons.append(
                "Transaction at unusual time"
            )

        if is_anomaly:

            reasons.append(
                "Transaction behavior is significantly "
                "different from normal patterns"
            )

        if not reasons:

            reasons.append(
                "No unusual transaction signals detected"
            )


        # ====================================================
        # 6. SHAP EXPLAINABLE AI
        # ====================================================

        try:

            shap_result = explainer(
                transaction
            )

            shap_values = (
                shap_result.values[0]
            )

            ai_explanation = []

            for feature, value in zip(
                features,
                shap_values
            ):

                value = float(value)

                ai_explanation.append(
                    {
                        "feature":
                            FEATURE_NAMES.get(
                                feature,
                                feature
                            ),

                        "contribution":
                            round(value, 4),

                        "effect":
                            (
                                "increases risk"
                                if value > 0
                                else "reduces risk"
                            ),
                    }
                )


            # Strongest factors first

            ai_explanation.sort(
                key=lambda item:
                    abs(
                        item["contribution"]
                    ),
                reverse=True
            )


            # Top 5 only

            ai_explanation = (
                ai_explanation[:5]
            )


        except Exception as error:

            # API should still work even
            # if SHAP explanation fails

            ai_explanation = []

            print(
                "SHAP Error:",
                str(error)
            )


        # ====================================================
        # 7. RECOMMENDATION
        # ====================================================

        if risk_level == "HIGH":

            recommendation = (
                "Verify the recipient "
                "before continuing."
            )

        elif risk_level == "MEDIUM":

            recommendation = (
                "Review the transaction "
                "details carefully."
            )

        else:

            recommendation = (
                "No significant risk detected."
            )


        # ====================================================
        # 8. API RESPONSE
        # ====================================================

        return Response(
            {
                "risk_score":
                    risk_score,

                "risk_level":
                    risk_level,

                "xgboost_score":
                    round(
                        xgb_score,
                        2
                    ),

                "fraud_probability":
                    round(
                        float(
                            fraud_probability
                        ),
                        4
                    ),

                "behavioral_anomaly":
                    bool(is_anomaly),

                "reasons":
                    reasons,

                "ai_explanation":
                    ai_explanation,

                "recommendation":
                    recommendation,
            },

            status=status.HTTP_200_OK,
        )