from django.urls import path
from .views import RiskPredictionView


urlpatterns = [
    path("predict/", RiskPredictionView.as_view(), name="predict-risk"),
]