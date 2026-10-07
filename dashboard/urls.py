from django.urls import path
from django.contrib.auth.views import LoginView, LogoutView
from . import views

urlpatterns = [
    path("", views.send_money, name="send-money"),
    path("warning/", views.warning, name="warning"),
    path("simulator/", views.simulator, name="simulator"),
    path(
        "analyst/login/",
        LoginView.as_view(template_name="dashboard/analyst_login.html"),
        name="analyst-login",
    ),
    path(
        "analyst/logout/",
        LogoutView.as_view(next_page="analyst-login"),
        name="analyst-logout",
    ),
    path("analyst/", views.analyst_dashboard, name="analyst-dashboard"),
    path(
        "analyst/transactions/<int:pk>/status/",
        views.update_analyst_status,
        name="analyst-update-status",
    ),
]