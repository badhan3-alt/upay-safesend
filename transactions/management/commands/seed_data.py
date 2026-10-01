import random
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from transactions.models import Transaction


class Command(BaseCommand):
    help = "Seeds realistic demo transactions into the database for testing and hackathon judging."

    def handle(self, *args, **options):
        self.stdout.write("Clearing previous transactions (if any)...")
        Transaction.objects.all().delete()

        now = timezone.now()
        demo_users = ["U0001", "U0002", "U0045", "U0120", "U0842"]
        known_recipients = ["R0101", "R0102", "R0205", "R0310", "01711223344", "01899887766"]
        risky_recipients = ["R9901", "R9942", "01300998877", "01999112233"]

        transactions_to_create = []

        # 1. Past normal transactions for primary demo user U0001
        for i in range(12):
            created_time = now - timedelta(days=random.randint(1, 45), hours=random.randint(1, 20))
            amount = round(random.uniform(500, 3500), 2)
            recipient = random.choice(known_recipients)
            tx = Transaction(
                transaction_id=f"UPAY-LEGACY-{1000 + i}",
                user_id="U0001",
                recipient_id=recipient,
                amount=amount,
                recipient_new=False,
                device_changed=False,
                location_changed=False,
                transactions_last_1h=1,
                average_transaction_amount=2450.00,
                account_age_days=random.randint(120, 300),
                risk_score=round(random.uniform(4.0, 14.5), 1),
                risk_level="LOW",
                is_suspicious=False,
            )
            transactions_to_create.append(tx)

        # 2. Add realistic mixed transactions for other users across different risk levels
        scenarios = [
            # High Risk Scam / Account Takeover attempts
            {
                "user": "U0001",
                "recipient": "01300998877",
                "amount": 38500.00,
                "new": True,
                "dev": True,
                "loc": True,
                "h_tx": 6,
                "score": 93.4,
                "level": "HIGH",
                "susp": True,
                "delta_hours": 2,
            },
            {
                "user": "U0045",
                "recipient": "R9942",
                "amount": 25000.00,
                "new": True,
                "dev": True,
                "loc": False,
                "h_tx": 4,
                "score": 87.2,
                "level": "HIGH",
                "susp": True,
                "delta_hours": 5,
            },
            {
                "user": "U0842",
                "recipient": "01999112233",
                "amount": 42000.00,
                "new": True,
                "dev": True,
                "loc": True,
                "h_tx": 7,
                "score": 96.8,
                "level": "HIGH",
                "susp": True,
                "delta_hours": 8,
            },
            # Medium Risk transfers
            {
                "user": "U0002",
                "recipient": "R0310",
                "amount": 8500.00,
                "new": False,
                "dev": True,
                "loc": False,
                "h_tx": 2,
                "score": 52.6,
                "level": "MEDIUM",
                "susp": False,
                "delta_hours": 12,
            },
            {
                "user": "U0120",
                "recipient": "R9901",
                "amount": 6200.00,
                "new": True,
                "dev": False,
                "loc": False,
                "h_tx": 2,
                "score": 44.1,
                "level": "MEDIUM",
                "susp": False,
                "delta_hours": 18,
            },
            # Normal Low Risk everyday transfers
            {
                "user": "U0002",
                "recipient": "01711223344",
                "amount": 1200.00,
                "new": False,
                "dev": False,
                "loc": False,
                "h_tx": 1,
                "score": 6.2,
                "level": "LOW",
                "susp": False,
                "delta_hours": 3,
            },
            {
                "user": "U0120",
                "recipient": "R0101",
                "amount": 2100.00,
                "new": False,
                "dev": False,
                "loc": False,
                "h_tx": 1,
                "score": 8.5,
                "level": "LOW",
                "susp": False,
                "delta_hours": 7,
            },
            {
                "user": "U0045",
                "recipient": "R0205",
                "amount": 1850.00,
                "new": False,
                "dev": False,
                "loc": False,
                "h_tx": 1,
                "score": 5.9,
                "level": "LOW",
                "susp": False,
                "delta_hours": 14,
            },
        ]

        for idx, s in enumerate(scenarios):
            tx = Transaction(
                transaction_id=f"UPAY-DEMO-{2000 + idx}",
                user_id=s["user"],
                recipient_id=s["recipient"],
                amount=s["amount"],
                recipient_new=s["new"],
                device_changed=s["dev"],
                location_changed=s["loc"],
                transactions_last_1h=s["h_tx"],
                average_transaction_amount=2500.00,
                account_age_days=180,
                risk_score=s["score"],
                risk_level=s["level"],
                is_suspicious=s["susp"],
            )
            transactions_to_create.append(tx)

        Transaction.objects.bulk_create(transactions_to_create)
        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully seeded {len(transactions_to_create)} demo transactions!"
            )
        )
