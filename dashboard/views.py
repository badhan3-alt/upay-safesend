from django.db.models import Sum
from django.shortcuts import render
from transactions.models import Transaction
import traceback


def send_money(request):
    """
    Simulated Upay Mobile Wallet client interface.
    """
    return render(request, "dashboard/send_money.html")


def warning(request):
    """
    SafeSend pre-transaction risk warning & explainability interception screen.
    """
    return render(request, "dashboard/warning.html")


def simulator(request):
    """
    Interactive AI Risk Engine & Explainability Simulator Lab.
    """
    return render(request, "dashboard/home.html")


def analyst_dashboard(request):
    """
    Fraud Operations & Investigation Copilot for Upay Security Analysts.
    """

    try:
        # ==============================
        # Dashboard statistics
        # ==============================

        total_count = Transaction.objects.count()

        low_count = Transaction.objects.filter(
            risk_level="LOW"
        ).count()

        med_count = Transaction.objects.filter(
            risk_level="MEDIUM"
        ).count()

        high_count = Transaction.objects.filter(
            risk_level="HIGH"
        ).count()

        total_volume = (
            Transaction.objects.aggregate(
                total=Sum("amount")
            )["total"]
            or 0
        )

        high_risk_volume = (
            Transaction.objects.filter(
                risk_level="HIGH"
            ).aggregate(
                total=Sum("amount")
            )["total"]
            or 0
        )

        # ==============================
        # Recent transactions
        # ==============================

        transactions = (
            Transaction.objects
            .all()
            .order_by("-created_at")[:100]
        )

        # ==============================
        # Template context
        # ==============================

        context = {
            "total_count": total_count,
            "low_count": low_count,
            "med_count": med_count,
            "high_count": high_count,
            "total_volume": float(total_volume),
            "high_risk_volume": float(high_risk_volume),
            "transactions": transactions,
            "dashboard_error": None,
        }

    except Exception as e:
        # Print full error in Render logs
        print("=" * 60)
        print("ANALYST DASHBOARD ERROR")
        print(str(e))
        traceback.print_exc()
        print("=" * 60)

        # Keep the dashboard page alive even if database access fails
        context = {
            "total_count": 0,
            "low_count": 0,
            "med_count": 0,
            "high_count": 0,
            "total_volume": 0.0,
            "high_risk_volume": 0.0,
            "transactions": [],
            "dashboard_error": str(e),
        }

    try:
        return render(
            request,
            "dashboard/analyst.html",
            context,
        )

    except Exception as e:
        # This catches template-related problems separately
        print("=" * 60)
        print("ANALYST TEMPLATE ERROR")
        print(str(e))
        traceback.print_exc()
        print("=" * 60)

        # Temporary readable fallback instead of generic Server Error 500
        from django.http import HttpResponse

        return HttpResponse(
            f"""
            <h1>SafeSend Analyst Dashboard</h1>
            <h2>Dashboard could not be rendered.</h2>
            <p><strong>Error:</strong> {str(e)}</p>
            <p>Check the Render logs for the full traceback.</p>
            """,
            status=500,
        )