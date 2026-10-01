from django.urls import path
from . import views

urlpatterns = [
    path("", views.send_money, name="send-money"),
    path("warning/", views.warning, name="warning"),
    path("simulator/", views.simulator, name="simulator"),
    path("analyst/", views.analyst_dashboard, name="analyst-dashboard"),
]