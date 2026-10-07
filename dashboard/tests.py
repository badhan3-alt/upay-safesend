from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from transactions.models import Transaction


class AnalystDashboardTests(TestCase):
    def setUp(self):
        self.transaction = Transaction.objects.create(
            transaction_id="UPAY-ANALYST-1",
            user_id="U0001",
            recipient_id="R0001",
            amount="399.00",
            risk_score=72,
            fraud_probability=0.61,
            anomaly_score=73,
            risk_level="HIGH",
            behavioral_anomaly=True,
            behavioral_features={"repeated_pattern_detected": True},
            risk_factors=["Repeated transfer pattern"],
            recommendation={"en": "Verify the recipient.", "bn": "প্রাপক যাচাই করুন।"},
        )
        group = Group.objects.create(name="Analyst")
        self.analyst = User.objects.create_user(
            username="analyst",
            password="strong-password",
        )
        self.analyst.groups.add(group)

    def test_simulator_exposes_behavioral_history_controls(self):
        response = self.client.get(reverse("simulator"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="csrfmiddlewaretoken"')
        self.assertContains(response, 'id="tx_10m"')
        self.assertContains(response, 'id="same_receiver_5m"')
        self.assertContains(response, 'id="same_receiver_10m"')
        self.assertContains(response, 'id="similar_amount_10m"')
        self.assertContains(response, 'id="time_since_last"')
        self.assertContains(response, 'id="recipient_frequency"')

    def test_dashboard_requires_analyst_login(self):
        response = self.client.get(reverse("analyst-dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/analyst/login/", response["Location"])

        self.client.force_login(self.analyst)
        response = self.client.get(reverse("analyst-dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "UPAY-ANALYST-1")
        self.assertContains(response, "Repeated transfer pattern")
        self.assertContains(response, "Fraud probability")
        self.assertContains(response, "Pending")

    def test_logged_in_non_analyst_is_forbidden(self):
        customer = User.objects.create_user(
            username="customer",
            password="strong-password",
        )
        self.client.force_login(customer)
        response = self.client.get(reverse("analyst-dashboard"))
        self.assertEqual(response.status_code, 403)

    def test_analyst_can_persist_review_status(self):
        self.client.force_login(self.analyst)
        response = self.client.post(
            reverse("analyst-update-status", args=[self.transaction.pk]),
            {"analyst_status": "ESCALATED"},
        )
        self.assertRedirects(response, reverse("analyst-dashboard"))

        self.transaction.refresh_from_db()
        self.assertEqual(self.transaction.analyst_status, "ESCALATED")

    def test_invalid_review_status_is_rejected(self):
        self.client.force_login(self.analyst)
        response = self.client.post(
            reverse("analyst-update-status", args=[self.transaction.pk]),
            {"analyst_status": "IGNORED"},
        )
        self.assertEqual(response.status_code, 400)
