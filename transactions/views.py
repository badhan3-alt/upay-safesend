from django.shortcuts import render

# Create your views here.
from rest_framework import generics

from risk_api.permissions import IsAnalyst
from .models import Transaction
from .serializers import TransactionSerializer


class TransactionListCreateView(generics.ListAPIView):
    queryset = Transaction.objects.all().order_by('-created_at')
    serializer_class = TransactionSerializer
    permission_classes = [IsAnalyst]