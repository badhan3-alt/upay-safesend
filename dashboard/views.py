from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.db.models import Sum
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from risk_api.permissions import is_analyst
from transactions.models import Recipient, Transaction


def analyst_required(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(
                request.get_full_path(),
                reverse("analyst-login"),
            )
        if not is_analyst(request.user):
            raise PermissionDenied("An analyst account is required.")
        return view(request, *args, **kwargs)

    return wrapped


def send_money(request):
    """Simulated Upay Mobile Wallet client interface."""
    recipients = Recipient.objects.filter(is_active=True).values_list(
        "recipient_id",
        flat=True,
    )
    return render(
        request,
        "dashboard/send_money.html",
        {"recipients": recipients},
    )


def warning(request):
    """SafeSend pre-transaction risk warning and explanation screen."""
    return render(request, "dashboard/warning.html")


def simulator(request):
    """Interactive AI risk engine and explanation simulator."""
    return render(request, "dashboard/home.html")


def analyst_dashboard(request):
    total_count = Transaction.objects.count()
    low_count = Transaction.objects.filter(risk_level="LOW").count()
    med_count = Transaction.objects.filter(risk_level="MEDIUM").count()
    high_count = Transaction.objects.filter(risk_level="HIGH").count()
    total_volume = Transaction.objects.aggregate(total=Sum("amount"))["total"] or 0
    high_risk_volume = (
        Transaction.objects.filter(risk_level="HIGH").aggregate(total=Sum("amount"))[
            "total"
        ]
        or 0
    )
    transactions = Transaction.objects.order_by("-created_at")[:100]

    return render(
        request,
        "dashboard/analyst.html",
        {
            "total_count": total_count,
            "low_count": low_count,
            "med_count": med_count,
            "high_count": high_count,
            "total_volume": float(total_volume),
            "high_risk_volume": float(high_risk_volume),
            "transactions": transactions,
            "analyst_statuses": Transaction.ANALYST_STATUSES,
            "can_manage_analyst": is_analyst(request.user),
        },
    )


@analyst_required
@require_POST
def update_analyst_status(request, pk):
    transaction = get_object_or_404(Transaction, pk=pk)
    requested_status = request.POST.get("analyst_status", "")
    valid_statuses = {value for value, _label in Transaction.ANALYST_STATUSES}
    if requested_status not in valid_statuses:
        return HttpResponseBadRequest("Invalid analyst status.")

    transaction.analyst_status = requested_status
    transaction.save(update_fields=["analyst_status"])
    return redirect("analyst-dashboard")
