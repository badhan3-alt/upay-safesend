from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from transactions.models import Transaction


class RiskApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

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
        self.assertIn("ai_explanation", data)
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
        self.assertTrue(len(data["ai_explanation"]) > 0)

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
        self.assertTrue(Transaction.objects.filter(recipient_id="01811223344").exists())

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
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        self.assertIn("stats", data)
        self.assertGreaterEqual(data["stats"]["total_transactions"], 1)
        self.assertGreaterEqual(data["stats"]["high_risk_count"], 1)
