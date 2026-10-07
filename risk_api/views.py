from datetime import timedelta
from decimal import Decimal
from math import exp
from pathlib import Path
import json
import uuid

from django.conf import settings
from django.db.models import Avg, Sum
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
import joblib
import pandas as pd
from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from transactions.models import Transaction
from model.feature_schema import MODEL_FEATURES
from .permissions import IsAnalyst
from .serializers import (
    ConfirmTransactionSerializer,
    RiskPredictionSerializer,
    SendMoneySerializer,
)

# ============================================================
# MODEL PATHS & PERSISTED ARTIFACTS
# ============================================================

MODEL_DIR = Path(settings.BASE_DIR) / "model" / "saved_models"
MODEL_PATH = MODEL_DIR / "fraud_xgboost.pkl"
FEATURE_PATH = MODEL_DIR / "features.pkl"
ANOMALY_MODEL_PATH = MODEL_DIR / "isolation_forest.pkl"
ANOMALY_CALIBRATION_PATH = MODEL_DIR / "anomaly_calibration.json"

xgb_model = joblib.load(MODEL_PATH)
features_list = joblib.load(FEATURE_PATH)
anomaly_model = joblib.load(ANOMALY_MODEL_PATH)
anomaly_scale = json.loads(
    ANOMALY_CALIBRATION_PATH.read_text(encoding="utf-8")
)["normal_positive_decision_p05"]
if features_list != MODEL_FEATURES:
    raise RuntimeError(
        "Saved model features do not match model/feature_schema.py; retrain the models."
    )


# ============================================================
# BEHAVIORAL VELOCITY / REPEATED-TRANSACTION DETECTION
# ============================================================

def detect_repeated_transactions(
    user_id,
    recipient_id,
    amount,
    window_minutes=10,
    similarity_tolerance=0.05,
    now=None,
):
    """
    Detect repeated or very similar transfers from the same user
    to the same recipient within a short time window.

    The current transaction is NOT yet stored, so a count of 2
    matching past transactions means the current attempt would be
    the 3rd similar transfer in the window.
    """
    now = now or timezone.now()
    window_start = now - timedelta(minutes=window_minutes)
    five_minutes_ago = now - timedelta(minutes=5)
    one_hour_ago = now - timedelta(hours=1)

    amount_decimal = Decimal(str(amount))
    tolerance = Decimal(str(similarity_tolerance))
    lower_bound = amount_decimal * (Decimal("1") - tolerance)
    upper_bound = amount_decimal * (Decimal("1") + tolerance)

    past_txns = Transaction.objects.filter(
        user_id=user_id,
        created_at__lt=now,
    )
    recent_10m = past_txns.filter(created_at__gte=window_start)
    recent_5m = past_txns.filter(created_at__gte=five_minutes_ago)
    recent_same_recipient = recent_10m.filter(recipient_id=recipient_id)
    similar_amount_count = recent_same_recipient.filter(
        amount__gte=lower_bound,
        amount__lte=upper_bound,
    ).count()
    last_transaction_at = past_txns.order_by("-created_at").values_list(
        "created_at", flat=True
    ).first()
    time_since_last_transaction = (
        max((now - last_transaction_at).total_seconds() / 60, 0)
        if last_transaction_at
        else 1440.0
    )
    average_amount = past_txns.aggregate(average=Avg("amount"))["average"]
    first_transaction_at = past_txns.order_by("created_at").values_list(
        "created_at", flat=True
    ).first()

    same_recipient_count_10m = recent_same_recipient.count()
    repeated_pattern_detected = similar_amount_count >= 2

    return {
        "window_minutes": window_minutes,
        "total_transactions_10m": recent_10m.count(),
        "same_receiver_count_5m": recent_5m.filter(
            recipient_id=recipient_id
        ).count(),
        "same_receiver_count_10m": same_recipient_count_10m,
        "same_recipient_count_10m": same_recipient_count_10m,
        "same_recipient_count": same_recipient_count_10m,
        "similar_amount_count": similar_amount_count,
        "similar_amount_count_10m": similar_amount_count,
        "transactions_last_1h": past_txns.filter(
            created_at__gte=one_hour_ago
        ).count(),
        "time_since_last_transaction": round(time_since_last_transaction, 2),
        "recipient_frequency": past_txns.filter(
            recipient_id=recipient_id
        ).count(),
        "average_transaction_amount": float(average_amount or 2500.0),
        "account_age_days": (
            max(10, (now - first_transaction_at).days)
            if first_transaction_at
            else 210
        ),
        "similarity_tolerance_percent": round(similarity_tolerance * 100, 1),
        "repeated_pattern_detected": repeated_pattern_detected,
    }


# ============================================================
# CORE RISK ENGINE (XGBoost + Isolation Forest + rule-based safety guardrails)
# ============================================================

def evaluate_transaction_risk(feature_data: dict) -> dict:
    """
    Computes model outputs, a distinct repetition guardrail, and explanations.
    """
    amount = float(feature_data.get("amount", 0))
    avg_amount = float(feature_data.get("average_transaction_amount", 2500))
    if avg_amount <= 0:
        avg_amount = 2500.0

    amount_ratio = round(amount / avg_amount, 2)
    recipient_new = int(bool(feature_data.get("recipient_new", False)))
    device_changed = int(bool(feature_data.get("device_changed", False)))
    location_changed = int(bool(feature_data.get("location_changed", False)))
    hour = int(feature_data.get("hour", 14))
    tx_last_1h = int(feature_data.get("transactions_last_1h", 1))
    account_age = int(feature_data.get("account_age_days", 180))

    total_transactions_10m = int(feature_data.get("total_transactions_10m", 0))
    same_recipient_count_5m = int(feature_data.get("same_receiver_count_5m", 0))
    similar_amount_count_10m = int(feature_data.get("similar_amount_count_10m", 0))
    same_recipient_count_10m = int(
        feature_data.get("same_receiver_count_10m", 0)
    )
    time_since_last_transaction = float(
        feature_data.get("time_since_last_transaction", 1440)
    )
    recipient_frequency = int(feature_data.get("recipient_frequency", 0))
    repeated_pattern_detected = bool(
        feature_data.get(
            "repeated_pattern_detected",
            similar_amount_count_10m >= 2,
        )
    )

    feature_values = {
        "amount": amount,
        "recipient_new": recipient_new,
        "hour": hour,
        "device_changed": device_changed,
        "location_changed": location_changed,
        "transactions_last_1h": tx_last_1h,
        "average_transaction_amount": avg_amount,
        "amount_ratio": amount_ratio,
        "account_age_days": account_age,
        "total_transactions_10m": total_transactions_10m,
        "same_receiver_count_5m": same_recipient_count_5m,
        "same_receiver_count_10m": same_recipient_count_10m,
        "similar_amount_count_10m": similar_amount_count_10m,
        "time_since_last_transaction": time_since_last_transaction,
        "recipient_frequency": recipient_frequency,
    }
    transaction_df = pd.DataFrame(
        [{feature: feature_values[feature] for feature in features_list}]
    )

    fraud_prob = float(xgb_model.predict_proba(transaction_df)[0][1])
    xgb_score = fraud_prob * 100.0

    anomaly_decision = float(anomaly_model.decision_function(transaction_df)[0])
    is_anomaly = bool(anomaly_decision < 0)
    if is_anomaly:
        anomaly_score = 50.0 + 50.0 * (1.0 - exp(anomaly_decision / anomaly_scale))
    else:
        anomaly_score = 50.0 * exp(-anomaly_decision / anomaly_scale)
    anomaly_score = max(0.0, min(100.0, anomaly_score))

    # The supervised probability is the risk score; anomaly output stays a
    # separate corroborating signal instead of being mixed through a fixed weight.
    ai_risk_score = xgb_score
    risk_floor = 70.0 if repeated_pattern_detected else 0.0
    risk_score = round(max(ai_risk_score, risk_floor), 1)

    # 4. Risk Level Calibration
    if risk_score >= 70.0:
        risk_level = "HIGH"
    elif risk_score >= 30.0:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    # 5. Rule-Based Explanations (Bilingual: English & Bangla)
    reasons_en = []
    reasons_bn = []

    if recipient_new:
        reasons_en.append("This is the first time you’re sending money to this recipient")
        reasons_bn.append("এই প্রাপককে আপনি আগে টাকা পাঠাননি")

    if amount_ratio >= 3.0:
        reasons_en.append(
            f"This amount is {amount_ratio:.1f}× higher than your usual transfer (৳{avg_amount:,.0f})"
        )
        reasons_bn.append(
            f"টাকার পরিমাণ আপনার সাধারণ লেনদেনের চেয়ে {amount_ratio:.1f} গুণ বেশি (সাধারণত ৳{avg_amount:,.0f})"
        )
    elif amount_ratio >= 1.8:
        reasons_en.append("This amount is higher than your usual transfer")
        reasons_bn.append("টাকার পরিমাণ আপনার সাধারণ লেনদেনের চেয়ে বেশি")

    if device_changed:
        reasons_en.append("This transfer is coming from a new or changed device")
        reasons_bn.append("নতুন বা পরিবর্তিত ডিভাইস থেকে এই লেনদেনটি করা হচ্ছে")

    if location_changed:
        reasons_en.append("This transfer is coming from an unusual location")
        reasons_bn.append("অপরিচিত কোনো স্থান থেকে এই লেনদেনটি করা হচ্ছে")

    if tx_last_1h >= 4:
        reasons_en.append(
            f"There have been {tx_last_1h} transfers in the past hour"
        )
        reasons_bn.append(
            f"গত এক ঘণ্টায় {tx_last_1h}টি লেনদেন হয়েছে"
        )

    if total_transactions_10m >= 3:
        reasons_en.append(
            f"This transfer would bring the 10-minute transaction count to "
            f"{total_transactions_10m + 1}"
        )
        reasons_bn.append(
            f"এই লেনদেনসহ ১০ মিনিটে মোট লেনদেন হবে {total_transactions_10m + 1}টি"
        )

    if repeated_pattern_detected:
        total_with_current = similar_amount_count_10m + 1
        reasons_en.append(
            f"Repeated transaction pattern detected: {total_with_current} similar "
            f"transfers were sent to this recipient within 10 minutes."
        )
        reasons_bn.append(
            f"পুনরাবৃত্ত লেনদেন শনাক্ত হয়েছে: ১০ মিনিটের মধ্যে এই প্রাপকের কাছে "
            f"{total_with_current}টি কাছাকাছি পরিমাণের লেনদেন"
        )

    if hour <= 5 or hour >= 23:
        reasons_en.append(f"This is an unusual time for a transfer ({hour:02d}:00)")
        reasons_bn.append(f"এই সময়টি লেনদেনের জন্য অস্বাভাবিক ({hour:02d}:০০)")

    if is_anomaly:
        reasons_en.append("This transfer looks different from the account’s usual activity")
        reasons_bn.append("অ্যাকাউন্টটির স্বাভাবিক লেনদেনের ধরন থেকে এটি কিছুটা আলাদা")

    if not reasons_en:
        reasons_en.append("This transfer looks similar to the account’s usual activity")
        reasons_bn.append("লেনদেনটি অ্যাকাউন্টটির নিয়মিত ব্যবহারের মতো")

    # 7. Actionable Recommendations (Good Project Test: What should Upay do next?)
    if risk_level == "HIGH":
        recommendation_en = (
            "Pause before sending. Call the recipient using a number you trust, especially if someone is pressuring you to act quickly."
        )
        recommendation_bn = (
            "টাকা পাঠানোর আগে একটু থামুন। পরিচিত নম্বরে প্রাপককে ফোন করে নিশ্চিত হোন—বিশেষ করে কেউ তাড়াহুড়ো করতে বললে।"
        )
    elif risk_level == "MEDIUM":
        recommendation_en = (
            "Take a moment to double-check the recipient and amount before you continue."
        )
        recommendation_bn = (
            "এগোনোর আগে প্রাপকের নম্বর ও টাকার পরিমাণ আরেকবার মিলিয়ে নিন।"
        )
    else:
        recommendation_en = "Nothing unusual stood out. If the recipient and amount are right, you can continue."
        recommendation_bn = "অস্বাভাবিক কিছু চোখে পড়েনি। প্রাপক ও টাকার পরিমাণ ঠিক থাকলে এগিয়ে যেতে পারেন।"

    # 8. Investigation Narrative (What happened? Why is it risky? What should Upay do next?)
    recipient_id = feature_data.get("recipient_id", "R0000")
    what_happened = (
        f"You’re sending ৳{amount:,.2f} to {recipient_id} at {hour:02d}:00."
    )
    if risk_level == "HIGH":
        why_risky = (
            "Several details stand out from what’s usual for this account. "
            "Please review the recipient, amount, and any recent changes before sending."
        )
        what_to_do = "Pause and confirm the recipient through a trusted contact method before deciding whether to continue."
        why_risky_bn = (
            "এই লেনদেনের কয়েকটি তথ্য অ্যাকাউন্টটির স্বাভাবিক ব্যবহারের থেকে আলাদা। "
            "পাঠানোর আগে প্রাপক, পরিমাণ ও সাম্প্রতিক পরিবর্তনগুলো দেখে নিন।"
        )
        what_to_do_bn = "একটু থামুন। এগোনোর আগে পরিচিত উপায়ে প্রাপকের সঙ্গে যোগাযোগ করে নিশ্চিত হোন।"
    elif risk_level == "MEDIUM":
        why_risky = (
            "A few details are different from what’s usual for this account. "
            "Check that the recipient and amount are what you intended."
        )
        what_to_do = "Double-check the recipient and amount. Continue only if both look right."
        why_risky_bn = (
            "এই লেনদেনের কিছু তথ্য অ্যাকাউন্টটির স্বাভাবিক ব্যবহারের থেকে আলাদা। "
            "প্রাপক ও টাকার পরিমাণ আপনার ইচ্ছামতো কি না দেখে নিন।"
        )
        what_to_do_bn = "প্রাপক ও টাকার পরিমাণ আরেকবার মিলিয়ে নিন। দুটিই ঠিক থাকলে এগিয়ে যান।"
    else:
        why_risky = "This transfer looks similar to the account’s usual activity."
        what_to_do = "No unusual activity stood out. You can continue if the recipient and amount are correct."
        why_risky_bn = "লেনদেনটি অ্যাকাউন্টটির নিয়মিত ব্যবহারের মতো মনে হচ্ছে।"
        what_to_do_bn = "অস্বাভাবিক কিছু চোখে পড়েনি। প্রাপক ও টাকার পরিমাণ ঠিক থাকলে এগিয়ে যেতে পারেন।"

    return {
        "risk_score": risk_score,
        "risk_level": risk_level,
        "ai_risk_score": round(ai_risk_score, 1),
        "xgboost_score": round(xgb_score, 2),
        "fraud_probability": round(fraud_prob, 4),
        "behavioral_anomaly": is_anomaly,
        "anomaly_score": round(anomaly_score, 2),
        "prediction_components": {
            "xgboost_fraud_probability": round(fraud_prob, 4),
            "isolation_forest_anomaly_score": round(anomaly_score, 2),
            "ai_risk_score": round(ai_risk_score, 1),
        },
        "safety_rules": {
            "repeated_transaction_detected": repeated_pattern_detected,
            "risk_score_floor": risk_floor,
        },
        "reasons": reasons_en,
        "reasons_bn": reasons_bn,
        "risk_factors": reasons_en,
        "recommendation": recommendation_en,
        "recommendation_bn": recommendation_bn,
        "features_analyzed": {
            "amount": amount,
            "recipient_new": bool(recipient_new),
            "hour": hour,
            "device_changed": bool(device_changed),
            "location_changed": bool(location_changed),
            "transactions_last_1h": tx_last_1h,
            "average_transaction_amount": round(avg_amount, 2),
            "amount_ratio": amount_ratio,
            "account_age_days": account_age,
            "total_transactions_10m": total_transactions_10m,
            "same_receiver_count_5m": same_recipient_count_5m,
            "same_recipient_transactions_10m": same_recipient_count_10m,
            "similar_amount_transactions_10m": similar_amount_count_10m,
            "time_since_last_transaction": time_since_last_transaction,
            "recipient_frequency": recipient_frequency,
            "repeated_pattern_detected": repeated_pattern_detected,
        },
        "behavioral_analysis": {
            "window_minutes": 10,
            "total_transactions_10m": total_transactions_10m,
            "same_receiver_count_5m": same_recipient_count_5m,
            "same_recipient_transactions_10m": same_recipient_count_10m,
            "similar_amount_transactions_10m": similar_amount_count_10m,
            "time_since_last_transaction": time_since_last_transaction,
            "repeated_pattern_detected": repeated_pattern_detected,
        },
        "investigation": {
            "what_happened": what_happened,
            "why_risky": why_risky,
            "what_upay_should_do": what_to_do,
        },
        "investigation_bn": {
            "what_happened": (
                f"আপনি {recipient_id}-কে ৳{amount:,.2f} পাঠাচ্ছেন ({hour:02d}:০০)।"
            ),
            "why_risky": why_risky_bn,
            "what_upay_should_do": what_to_do_bn,
        },
    }


# ============================================================
# API VIEWS
# ============================================================

@method_decorator(csrf_protect, name="dispatch")
class RiskPredictionView(generics.GenericAPIView):
    """
    Direct feature risk prediction API for simulators, test suites, and third-party integrations.
    """
    serializer_class = RiskPredictionSerializer
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = evaluate_transaction_risk(serializer.validated_data)
        return Response(result, status=status.HTTP_200_OK)


@method_decorator(csrf_protect, name="dispatch")
class SendMoneyRiskView(generics.GenericAPIView):
    """
    Context-aware risk check API for the Upay mobile app.
    Automatically calculates user baseline from past database transactions.
    """
    serializer_class = SendMoneySerializer
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        user_id = data["user_id"]
        recipient_id = data["recipient_id"]
        amount = float(data["amount"])
        behavior = detect_repeated_transactions(
            user_id=user_id,
            recipient_id=recipient_id,
            amount=amount,
        )

        # Determine transaction hour
        if data.get("hour") is not None:
            hour = data["hour"]
        else:
            hour = timezone.localtime().hour

        device_changed = data.get("device_changed", False)
        location_changed = data.get("location_changed", False)

        feature_data = {
            **behavior,
            "user_id": user_id,
            "recipient_id": recipient_id,
            "amount": amount,
            "recipient_new": behavior["recipient_frequency"] == 0,
            "hour": hour,
            "device_changed": device_changed,
            "location_changed": location_changed,
        }

        result = evaluate_transaction_risk(feature_data)
        result["user_id"] = user_id
        result["recipient_id"] = recipient_id
        result["amount"] = amount

        return Response(result, status=status.HTTP_200_OK)


@method_decorator(csrf_protect, name="dispatch")
class ConfirmTransactionView(generics.GenericAPIView):
    """
    Records and finalizes the transaction in the database once the user confirms or verifies it.
    """
    serializer_class = ConfirmTransactionSerializer
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        txn_id = f"UPAY-{uuid.uuid4().hex[:8].upper()}"
        behavior = detect_repeated_transactions(
            user_id=data["user_id"],
            recipient_id=data["recipient_id"],
            amount=data["amount"],
        )
        feature_data = {
            **behavior,
            "user_id": data["user_id"],
            "recipient_id": data["recipient_id"],
            "amount": float(data["amount"]),
            "recipient_new": behavior["recipient_frequency"] == 0,
            "hour": (
                data["hour"]
                if data["hour"] is not None
                else timezone.localtime().hour
            ),
            "device_changed": data["device_changed"],
            "location_changed": data["location_changed"],
        }
        result = evaluate_transaction_risk(feature_data)
        analyzed = result["features_analyzed"]

        txn = Transaction.objects.create(
            transaction_id=txn_id,
            user_id=data["user_id"],
            recipient_id=data["recipient_id"],
            amount=data["amount"],
            recipient_new=analyzed["recipient_new"],
            device_changed=data["device_changed"],
            location_changed=data["location_changed"],
            transactions_last_1h=analyzed["transactions_last_1h"],
            average_transaction_amount=analyzed["average_transaction_amount"],
            account_age_days=analyzed["account_age_days"],
            risk_score=result["risk_score"],
            fraud_probability=result["fraud_probability"],
            anomaly_score=result["anomaly_score"],
            risk_level=result["risk_level"],
            is_suspicious=result["risk_level"] == "HIGH",
            behavioral_anomaly=result["behavioral_anomaly"],
            behavioral_features=analyzed,
            risk_factors=result["risk_factors"],
            recommendation={
                "en": result["recommendation"],
                "bn": result["recommendation_bn"],
            },
            user_verified=data["verified_by_user"],
        )

        return Response(
            {
                "status": "SUCCESS",
                "message": "Transaction completed successfully.",
                "message_bn": "লেনদেনটি সফলভাবে সম্পন্ন হয়েছে।",
                "transaction_id": txn.transaction_id,
                "amount": float(txn.amount),
                "recipient_id": txn.recipient_id,
                "risk_score": txn.risk_score,
                "risk_level": txn.risk_level,
                "fraud_probability": txn.fraud_probability,
                "anomaly_score": txn.anomaly_score,
                "behavioral_analysis": result["behavioral_analysis"],
                "timestamp": txn.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            },
            status=status.HTTP_201_CREATED,
        )


class TransactionStatsView(APIView):
    """
    Returns live statistics for the Analyst Operations Dashboard:
    Total count, risk breakdown, high-risk volume, and recent transactions.
    """
    permission_classes = [IsAnalyst]

    def get(self, request):
        total_txns = Transaction.objects.count()
        low_txns = Transaction.objects.filter(risk_level="LOW").count()
        med_txns = Transaction.objects.filter(risk_level="MEDIUM").count()
        high_txns = Transaction.objects.filter(risk_level="HIGH").count()

        total_vol = Transaction.objects.aggregate(Sum("amount"))["amount__sum"] or 0
        high_risk_vol = (
            Transaction.objects.filter(risk_level="HIGH").aggregate(Sum("amount"))[
                "amount__sum"
            ]
            or 0
        )

        recent = (
            Transaction.objects.all()
            .order_by("-created_at")[:50]
            .values(
                "id",
                "transaction_id",
                "user_id",
                "recipient_id",
                "amount",
                "risk_score",
                "fraud_probability",
                "anomaly_score",
                "behavioral_anomaly",
                "risk_level",
                "is_suspicious",
                "analyst_status",
                "created_at",
                "recipient_new",
                "device_changed",
                "location_changed",
                "behavioral_features",
                "risk_factors",
                "recommendation",
            )
        )

        return Response(
            {
                "stats": {
                    "total_transactions": total_txns,
                    "safe_count": low_txns,
                    "suspicious_count": med_txns,
                    "high_risk_count": high_txns,
                    "total_volume": float(total_vol),
                    "high_risk_volume": float(high_risk_vol),
                },
                "recent_transactions": list(recent),
            },
            status=status.HTTP_200_OK,
        )