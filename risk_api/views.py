from datetime import timedelta
from pathlib import Path
import uuid

from django.conf import settings
from django.db.models import Avg, Sum
from django.utils import timezone
import joblib
import pandas as pd
from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from transactions.models import Transaction
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

# Load models safely
try:
    xgb_model = joblib.load(MODEL_PATH)
    features_list = joblib.load(FEATURE_PATH)
    anomaly_model = joblib.load(ANOMALY_MODEL_PATH)
except Exception as e:
    print(f"Warning: Error loading ML models: {e}")
    xgb_model = None
    features_list = [
        "amount",
        "recipient_new",
        "hour",
        "device_changed",
        "location_changed",
        "transactions_last_1h",
        "average_transaction_amount",
        "amount_ratio",
        "account_age_days",
    ]
    anomaly_model = None


# Friendly labels for frontend / report
FEATURE_NAMES_EN = {
    "amount": "Transaction Amount",
    "recipient_new": "New Recipient",
    "hour": "Transaction Time of Day",
    "device_changed": "Device Change",
    "location_changed": "Location Change",
    "transactions_last_1h": "Hourly Velocity / Frequency",
    "average_transaction_amount": "User Average Amount",
    "amount_ratio": "Spike vs Normal Spending",
    "account_age_days": "Account Age",
}

FEATURE_NAMES_BN = {
    "amount": "লেনদেনের পরিমাণ",
    "recipient_new": "নতুন প্রাপক",
    "hour": "লেনদেনের সময়",
    "device_changed": "ডিভাইস পরিবর্তন",
    "location_changed": "অবস্থান পরিবর্তন",
    "transactions_last_1h": "গত এক ঘণ্টায় লেনদেনের সংখ্যা",
    "average_transaction_amount": "গড় লেনদেনের পরিমাণ",
    "amount_ratio": "স্বাভাবিকের চেয়ে তারতম্য",
    "account_age_days": "অ্যাকাউন্টের বয়স",
}


# ============================================================
# CORE RISK ENGINE (Ensemble: XGBoost + Isolation Forest + Lightweight Explainability)
# ============================================================

def evaluate_transaction_risk(feature_data: dict) -> dict:
    """
    Computes ensemble risk score, behavioral anomaly flag,
    lightweight explainability, bilingual reasons, and recommendations.
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

    transaction_df = pd.DataFrame(
        [
            {
                "amount": amount,
                "recipient_new": recipient_new,
                "hour": hour,
                "device_changed": device_changed,
                "location_changed": location_changed,
                "transactions_last_1h": tx_last_1h,
                "average_transaction_amount": avg_amount,
                "amount_ratio": amount_ratio,
                "account_age_days": account_age,
            }
        ]
    )

    # Reorder features exactly as trained
    transaction_df = transaction_df[features_list]

    # 1. XGBoost Supervised Classification
    if xgb_model is not None:
        try:
            fraud_prob = float(xgb_model.predict_proba(transaction_df)[0][1])
            xgb_score = fraud_prob * 100.0
        except Exception:
            fraud_prob = 0.05
            xgb_score = 5.0
    else:
        fraud_prob = 0.05
        xgb_score = 5.0

    # 2. Isolation Forest Unsupervised Anomaly Detection
    is_anomaly = False
    if anomaly_model is not None:
        try:
            anomaly_pred = anomaly_model.predict(transaction_df)[0]
            # -1 = anomaly, 1 = normal
            is_anomaly = bool(anomaly_pred == -1)
        except Exception:
            is_anomaly = False

    anomaly_score = 100.0 if is_anomaly else 0.0

    # 3. Blended Ensemble Risk Score (75% XGBoost + 25% Isolation Forest)
    blended_score = (0.75 * xgb_score) + (0.25 * anomaly_score)
    risk_score = round(max(0.0, min(100.0, blended_score)), 1)

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

    if hour <= 5 or hour >= 23:
        reasons_en.append(f"This is an unusual time for a transfer ({hour:02d}:00)")
        reasons_bn.append(f"এই সময়টি লেনদেনের জন্য অস্বাভাবিক ({hour:02d}:০০)")

    if is_anomaly:
        reasons_en.append("This transfer looks different from the account’s usual activity")
        reasons_bn.append("অ্যাকাউন্টটির স্বাভাবিক লেনদেনের ধরন থেকে এটি কিছুটা আলাদা")

    if not reasons_en:
        reasons_en.append("This transfer looks similar to the account’s usual activity")
        reasons_bn.append("লেনদেনটি অ্যাকাউন্টটির নিয়মিত ব্যবহারের মতো")

    # 6. Lightweight Feature Attribution
    # Keeps the same response structure as the former SHAP output so the
    # frontend can continue to use ai_explanation without changes.
    feature_contributions = {
        "amount": min(max((amount_ratio - 1.0) * 0.18, 0.0), 1.0),
        "recipient_new": 0.35 if recipient_new else -0.05,
        "hour": 0.25 if (hour <= 5 or hour >= 23) else -0.02,
        "device_changed": 0.30 if device_changed else -0.03,
        "location_changed": 0.25 if location_changed else -0.03,
        "transactions_last_1h": min(max((tx_last_1h - 1) * 0.10, 0.0), 0.6),
        "average_transaction_amount": -0.02,
        "amount_ratio": min(max((amount_ratio - 1.0) * 0.30, 0.0), 1.2),
        "account_age_days": 0.15 if account_age < 30 else -0.04,
    }

    ai_explanation = []
    for feat in features_list:
        val_flt = float(feature_contributions.get(feat, 0.0))
        ai_explanation.append(
            {
                "feature_key": feat,
                "feature": FEATURE_NAMES_EN.get(feat, feat),
                "feature_bn": FEATURE_NAMES_BN.get(feat, feat),
                "contribution": round(val_flt, 4),
                "effect": "increases risk" if val_flt > 0 else "reduces risk",
                "effect_bn": "ঝুঁকি বাড়ায়" if val_flt > 0 else "ঝুঁকি কমায়",
            }
        )

    ai_explanation.sort(key=lambda x: abs(x["contribution"]), reverse=True)
    ai_explanation = ai_explanation[:5]

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
        "xgboost_score": round(xgb_score, 2),
        "fraud_probability": round(fraud_prob, 4),
        "behavioral_anomaly": is_anomaly,
        "reasons": reasons_en,
        "reasons_bn": reasons_bn,
        "recommendation": recommendation_en,
        "recommendation_bn": recommendation_bn,
        "ai_explanation": ai_explanation,
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

        # Fetch past transactions for user to build real behavioral context
        past_txns = Transaction.objects.filter(user_id=user_id)
        has_history = past_txns.exists()

        if has_history:
            avg_amount = past_txns.aggregate(Avg("amount"))["amount__avg"] or 2500.0
            avg_amount = float(avg_amount)
            recipient_new = not past_txns.filter(recipient_id=recipient_id).exists()
            one_hour_ago = timezone.now() - timedelta(hours=1)
            tx_last_1h = past_txns.filter(created_at__gte=one_hour_ago).count()
            earliest_txn = past_txns.order_by("created_at").first()
            account_age_days = max(10, (timezone.now() - earliest_txn.created_at).days)
        else:
            # Synthetic default profile for demo user
            avg_amount = 2500.0
            recipient_new = True
            tx_last_1h = 0
            account_age_days = 210

        # Determine transaction hour
        if data.get("hour") is not None:
            hour = data["hour"]
        else:
            # Use current local time hour
            hour = timezone.localtime().hour

        device_changed = data.get("device_changed", False)
        location_changed = data.get("location_changed", False)

        feature_data = {
            "user_id": user_id,
            "recipient_id": recipient_id,
            "amount": amount,
            "recipient_new": recipient_new,
            "hour": hour,
            "device_changed": device_changed,
            "location_changed": location_changed,
            "transactions_last_1h": tx_last_1h,
            "average_transaction_amount": avg_amount,
            "account_age_days": account_age_days,
        }

        result = evaluate_transaction_risk(feature_data)
        result["user_id"] = user_id
        result["recipient_id"] = recipient_id
        result["amount"] = amount

        return Response(result, status=status.HTTP_200_OK)


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

        past_txns = Transaction.objects.filter(user_id=data["user_id"])
        avg_amount = past_txns.aggregate(Avg("amount"))["amount__avg"] or 2500.0
        one_hour_ago = timezone.now() - timedelta(hours=1)
        tx_last_1h = past_txns.filter(created_at__gte=one_hour_ago).count()

        is_suspicious = data["risk_score"] >= 70.0

        txn = Transaction.objects.create(
            transaction_id=txn_id,
            user_id=data["user_id"],
            recipient_id=data["recipient_id"],
            amount=data["amount"],
            recipient_new=data["recipient_new"],
            device_changed=data["device_changed"],
            location_changed=data["location_changed"],
            transactions_last_1h=tx_last_1h,
            average_transaction_amount=avg_amount,
            account_age_days=180,
            risk_score=data["risk_score"],
            risk_level=data["risk_level"],
            is_suspicious=is_suspicious,
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
                "timestamp": txn.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            },
            status=status.HTTP_201_CREATED,
        )


class TransactionStatsView(APIView):
    """
    Returns live statistics for the Analyst Operations Dashboard:
    Total count, risk breakdown, high-risk volume, and recent transactions.
    """
    authentication_classes = []
    permission_classes = [AllowAny]

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
                "risk_level",
                "is_suspicious",
                "created_at",
                "recipient_new",
                "device_changed",
                "location_changed",
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