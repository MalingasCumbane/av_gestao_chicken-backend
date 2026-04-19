from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.utils import timezone
from .models import Batch, Client, Expense, Loss, Sale
from .serializers import (
    ClientSerializer, ExpenseSerializer, LossSerializer, SaleSerializer,
    BatchListSerializer, BatchDetailSerializer, BatchCreateUpdateSerializer,
    SlaughterSerializer, PaymentConfirmationSerializer
)
from .permissions import IsOwner

class BatchListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = BatchListSerializer

    def get_queryset(self):
        return Batch.objects.filter(user=self.request.user).order_by('-created_at')

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return BatchCreateUpdateSerializer
        return BatchListSerializer

class BatchDetailView(generics.RetrieveUpdateAPIView):
    permission_classes = [permissions.IsAuthenticated, IsOwner]
    queryset = Batch.objects.all()
    lookup_field = 'id'

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return BatchCreateUpdateSerializer
        return BatchDetailSerializer

class BatchAddExpenseView(generics.CreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ExpenseSerializer

    def perform_create(self, serializer):
        batch = get_object_or_404(Batch, id=self.kwargs['batch_id'], user=self.request.user)
        serializer.save(batch=batch)

class BatchAddLossView(generics.CreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = LossSerializer

    def perform_create(self, serializer):
        batch = get_object_or_404(Batch, id=self.kwargs['batch_id'], user=self.request.user)
        serializer.save(batch=batch)

class BatchSlaughterView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request, batch_id):
        batch = get_object_or_404(Batch, id=batch_id, user=request.user, status='active')
        serializer = SlaughterSerializer(data=request.data, context={'batch': batch})
        serializer.is_valid(raise_exception=True)
        quantity = serializer.validated_data['quantity']
        batch.frozen_count += quantity
        batch.save(update_fields=['frozen_count'])
        return Response({'message': f'{quantity} frangos abatidos/congelados com sucesso.'})

class SaleListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = SaleSerializer

    def get_queryset(self):
        return Sale.objects.filter(batch__user=self.request.user).order_by('-date')

    def perform_create(self, serializer):
        # O batch já é validado no serializer
        serializer.save()

class SalePaymentConfirmView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def patch(self, request, sale_id):
        sale = get_object_or_404(Sale, id=sale_id, batch__user=request.user)
        if sale.payment_status == 'paid':
            return Response({'detail': 'Venda já está paga.'}, status=status.HTTP_400_BAD_REQUEST)
        serializer = PaymentConfirmationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        sale.payment_status = 'paid'
        sale.paid_date = serializer.validated_data.get('paid_date', timezone.now().date())
        sale.save(update_fields=['payment_status', 'paid_date'])
        return Response({'message': 'Pagamento confirmado.'})

class ClientListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ClientSerializer

    def get_queryset(self):
        return Client.objects.filter(user=self.request.user).order_by('name')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class ClientDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [permissions.IsAuthenticated, IsOwner]
    queryset = Client.objects.all()
    serializer_class = ClientSerializer
    lookup_field = 'id'

class PendingPaymentsListView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = SaleSerializer

    def get_queryset(self):
        today = timezone.now().date()
        return Sale.objects.filter(
            batch__user=self.request.user,
            payment_status='pending'
        ).order_by('payment_due_date')