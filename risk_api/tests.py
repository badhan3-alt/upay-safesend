from datetime import timedelta

from unittest.mock import patch

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient
from transactions.models import Recipient, Transaction


class RiskApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        for recipient_id in ("R0001", "01811223344", "01799887766"):
            Recipient.objects.create(recipient_id=recipient_id)

    def create_transaction(self, transaction_id, created_at, **overrides):
        values = {
            "transaction_id": transaction_id,
            "user_id": "U0001",
            "recipient_id": "R0001",
            "amount": "399.00",
            "risk_score": 10,
            "risk_level": "LOW",
        }
        values.update(overrides)
        txn = Transaction.objects.create(**values)
        Transaction.objects.filter(pk=txn.pk).update(created_at=created_at)
        return txn

    def test_risk_prediction_normal_transaction(self):
        url = reverse("predict-risk")
        payload = {
            "amount": 1200.0,
            "average_transaction_amount": 2500.0,
            "hour": 14,
            "transactions_last_1h": 1,
            "account_age_days": 240,
            "recipient_new": False,
            "device_changed": False,
            "location_changed": False,
        }
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        self.assertIn("risk_score", data)
        self.assertIn("risk_level", data)
        self.assertEqual(data["risk_level"], "LOW")
        self.assertIn("risk_factors", data)
        self.assertIn("prediction_components", data)
        self.assertIn("anomaly_score", data)
        self.assertIn("reasons_bn", data)
        self.assertIn("investigation", data)
        self.assertIn("investigation_bn", data)
        self.assertIn("what_upay_should_do", data["investigation_bn"])
        self.assertIn(
            "অস্বাভাবিক কিছু চোখে পড়েনি",
            data["investigation_bn"]["what_upay_should_do"],
        )

    def test_risk_prediction_high_risk_scam(self):
        url = reverse("predict-risk")
        payload = {
            "amount": 45000.0,
            "average_transaction_amount": 2000.0,
            "hour": 3,
            "transactions_last_1h": 6,
            "account_age_days": 180,
            "recipient_new": True,
            "device_changed": True,
            "location_changed": True,
        }
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        self.assertGreaterEqual(data["risk_score"], 70.0)
        self.assertEqual(data["risk_level"], "HIGH")
        self.assertTrue(len(data["reasons"]) > 0)
        self.assertTrue(len(data["risk_factors"]) > 0)

    def test_simulator_repeated_pattern_uses_supplied_behavioral_features(self):
        response = self.client.post(
            reverse("predict-risk"),
            {
                "amount": "399.00",
                "average_transaction_amount": 2500,
                "hour": 14,
                "transactions_last_1h": 3,
                "account_age_days": 240,
                "recipient_new": False,
                "device_changed": False,
                "location_changed": False,
                "total_transactions_10m": 3,
                "same_receiver_count_5m": 2,
                "same_receiver_count_10m": 2,
                "similar_amount_count_10m": 2,
                "time_since_last_transaction": 2,
                "recipient_frequency": 6,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["features_analyzed"]["total_transactions_10m"], 3)
        self.assertEqual(
            response.data["behavioral_analysis"]["similar_amount_transactions_10m"],
            2,
        )
        self.assertTrue(
            response.data["safety_rules"]["repeated_transaction_detected"]
        )
        self.assertGreaterEqual(response.data["risk_score"], 70)
        self.assertTrue(
            any("3 similar transfers" in reason for reason in response.data["reasons"])
        )

    def test_send_money_endpoint(self):
        url = reverse("send-money-risk")
        payload = {
            "user_id": "U0001",
            "recipient_id": "01799887766",
            "amount": 28000.0,
            "device_changed": True,
            "location_changed": False,
            "hour": 2,
        }
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        self.assertEqual(data["user_id"], "U0001")
        self.assertEqual(data["recipient_id"], "01799887766")
        self.assertIn("risk_score", data)
        self.assertIn("investigation", data)
        self.assertIn("total_transactions_10m", data["features_analyzed"])

    def test_repeated_similar_transfers_are_detected_from_database_history(self):
        now = timezone.now()
        self.create_transaction(
            "UPAY-REPEAT-1",
            now - timedelta(minutes=8),
            amount="399.00",
        )
        self.create_transaction(
            "UPAY-REPEAT-2",
            now - timedelta(minutes=3),
            amount="405.00",
        )

        with patch("risk_api.views.timezone.now", return_value=now):
            response = self.client.post(
                reverse("send-money-risk"),
                {
                    "user_id": "U0001",
                    "recipient_id": "R0001",
                    "amount": "399.00",
                    "hour": 14,
                },
                format="json",
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["behavioral_analysis"]["repeated_pattern_detected"])
        self.assertEqual(
            response.data["behavioral_analysis"]["similar_amount_transactions_10m"],
            2,
        )
        self.assertEqual(response.data["features_analyzed"]["same_receiver_count_5m"], 1)
        self.assertGreaterEqual(response.data["risk_score"], 70)
        self.assertTrue(
            any("3 similar transfers" in reason for reason in response.data["reasons"])
        )

    def test_repeated_detection_excludes_other_senders_and_expired_transactions(self):
        now = timezone.now()
        self.create_transaction(
            "UPAY-OLD",
            now - timedelta(minutes=11),
            amount="399.00",
        )
        self.create_transaction(
            "UPAY-OTHER-USER",
            now - timedelta(minutes=2),
            amount="399.00",
            user_id="U0002",
        )

        with patch("risk_api.views.timezone.now", return_value=now):
            response = self.client.post(
                reverse("send-money-risk"),
                {
                    "user_id": "U0001",
                    "recipient_id": "R0001",
                    "amount": "399.00",
                    "hour": 14,
                },
                format="json",
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        behavior = response.data["behavioral_analysis"]
        self.assertEqual(behavior["similar_amount_transactions_10m"], 0)
        self.assertFalse(behavior["repeated_pattern_detected"])

    def test_confirm_transaction_endpoint(self):
        url = reverse("confirm-transaction")
        payload = {
            "user_id": "U0001",
            "recipient_id": "01811223344",
            "amount": 1500.0,
            "risk_score": 12.5,
            "risk_level": "LOW",
            "recipient_new": False,
            "device_changed": False,
            "location_changed": False,
            "verified_by_user": True,
        }
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], "SUCCESS")
        txn = Transaction.objects.get(recipient_id="01811223344")
        self.assertTrue(txn.user_verified)
        self.assertEqual(txn.risk_score, response.data["risk_score"])
        self.assertEqual(txn.risk_level, response.data["risk_level"])
        self.assertIsInstance(txn.behavioral_features, dict)
        self.assertIsInstance(txn.risk_factors, list)

    def test_confirm_ignores_client_supplied_risk_values(self):
        now = timezone.now()
        self.create_transaction(
            "UPAY-PRECONFIRM-1",
            now - timedelta(minutes=7),
            amount="399.00",
        )
        self.create_transaction(
            "UPAY-PRECONFIRM-2",
            now - timedelta(minutes=2),
            amount="399.00",
        )

        response = self.client.post(
            reverse("confirm-transaction"),
            {
                "user_id": "U0001",
                "recipient_id": "R0001",
                "amount": "399.00",
                "risk_score": 0,
                "risk_level": "LOW",
                "verified_by_user": True,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertGreaterEqual(response.data["risk_score"], 70)
        self.assertEqual(response.data["risk_level"], "HIGH")

    def test_transaction_submission_validates_amount_and_sender(self):
        url = reverse("send-money-risk")
        invalid_amount = self.client.post(
            url,
            {"user_id": "U0001", "recipient_id": "R0001", "amount": "0"},
            format="json",
        )
        self.assertEqual(invalid_amount.status_code, status.HTTP_400_BAD_REQUEST)

        self_transfer = self.client.post(
            url,
            {"user_id": "U0001", "recipient_id": "U0001", "amount": "100"},
            format="json",
        )
        self.assertEqual(self_transfer.status_code, status.HTTP_400_BAD_REQUEST)

        malformed_recipient = self.client.post(
            url,
            {"user_id": "U0001", "recipient_id": "invalid id", "amount": "100"},
            format="json",
        )
        self.assertEqual(malformed_recipient.status_code, status.HTTP_400_BAD_REQUEST)

        unknown_recipient = self.client.post(
            url,
            {"user_id": "U0001", "recipient_id": "R9999", "amount": "100"},
            format="json",
        )
        self.assertEqual(unknown_recipient.status_code, status.HTTP_400_BAD_REQUEST)

    def test_prediction_endpoint_is_post_only(self):
        response = self.client.get(reverse("predict-risk"))
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_browser_risk_submission_requires_csrf_token(self):
        client = APIClient(enforce_csrf_checks=True)
        payload = {
            "user_id": "U0001",
            "recipient_id": "R0001",
            "amount": "1500.00",
        }
        denied = client.post(
            reverse("send-money-risk"),
            payload,
            format="json",
        )
        self.assertEqual(denied.status_code, status.HTTP_403_FORBIDDEN)

        client.get(reverse("send-money"))
        token = client.cookies["csrftoken"].value
        accepted = client.post(
            reverse("send-money-risk"),
            payload,
            format="json",
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(accepted.status_code, status.HTTP_200_OK)

    def test_transaction_stats_endpoint(self):
        # Create sample transaction
        Transaction.objects.create(
            transaction_id="UPAY-TEST-1",
            user_id="U0001",
            recipient_id="R0001",
            amount=5000.0,
            risk_score=85.0,
            risk_level="HIGH",
            is_suspicious=True,
        )
        url = reverse("transaction-stats")
        self.assertEqual(
            self.client.get(url).status_code,
            status.HTTP_403_FORBIDDEN,
        )
        analyst_group = Group.objects.create(name="Analyst")
        analyst = User.objects.create_user(
            username="analyst",
            password="strong-password",
        )
        analyst.groups.add(analyst_group)
        self.client.force_authenticate(user=analyst)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        self.assertIn("stats", data)
        self.assertGreaterEqual(data["stats"]["total_transactions"], 1)
        self.assertGreaterEqual(data["stats"]["high_risk_count"], 1)
        self.assertIn("fraud_probability", data["recent_transactions"][0])
        self.assertEqual(
            self.client.get(reverse("transaction-list-create")).status_code,
            status.HTTP_200_OK,
        )
