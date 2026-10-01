from django.db.models import Sum
from django.shortcuts import render
from transactions.models import Transaction


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
    Interactive AI Risk Engine & SHAP Explainer Simulator Lab.
    """
    return render(request, "dashboard/home.html")


def analyst_dashboard(request):
    """
    Fraud Operations & Investigation Copilot for Upay Security Analysts.
    """
    total_count = Transaction.objects.count()
    low_count = Transaction.objects.filter(risk_level="LOW").count()
    med_count = Transaction.objects.filter(risk_level="MEDIUM").count()
    high_count = Transaction.objects.filter(risk_level="HIGH").count()
    total_volume = Transaction.objects.aggregate(Sum("amount"))["amount__sum"] or 0
    high_risk_volume = (
        Transaction.objects.filter(risk_level="HIGH").aggregate(Sum("amount"))[
            "amount__sum"
        ]
        or 0
    )

    transactions = Transaction.objects.all().order_by("-created_at")[:100]

    context = {
        "total_count": total_count,
        "low_count": low_count,
        "med_count": med_count,
        "high_count": high_count,
        "total_volume": float(total_volume),
        "high_risk_volume": float(high_risk_volume),
        "transactions": transactions,
    }
    return render(request, "dashboard/analyst.html", context)