"""
URL configuration for safesend project.
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("dashboard.urls")),
    path("api/transactions/", include("transactions.urls")),
    path("api/risk/", include("risk_api.urls")),
]