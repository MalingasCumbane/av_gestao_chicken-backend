from django.urls import path
from . import views

urlpatterns = [
    # Batches
    path('batches/', views.BatchListCreateView.as_view(), name='batch-list'), # OK
    path('batches/<int:id>/', views.BatchDetailView.as_view(), name='batch-detail'), # OK
    path('batches/<int:batch_id>/expenses/', views.BatchAddExpenseView.as_view(), name='batch-add-expense'), # OK
    path('batches/<int:batch_id>/losses/', views.BatchAddLossView.as_view(), name='batch-add-loss'), # OK
    path('batches/<int:batch_id>/slaughter/', views.BatchSlaughterView.as_view(), name='batch-slaughter'), # OK

    # Sales
    path('sales/', views.SaleListCreateView.as_view(), name='sale-list'),
    path('sales/<int:sale_id>/pay/', views.SalePaymentConfirmView.as_view(), name='sale-pay'),
    path('sales/pending/', views.PendingPaymentsListView.as_view(), name='pending-payments'),

    # Clients
    path('clients/', views.ClientListCreateView.as_view(), name='client-list'),
    path('clients/<int:id>/', views.ClientDetailView.as_view(), name='client-detail'),
    path('health/', views.HealthMonitorAPIView.as_view(), name='app-health-detail'),
]