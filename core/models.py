import uuid
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal
from common.models import LifeCycle


class Client(LifeCycle):
    TYPE_CHOICES = [('individual', 'Individual'), ('company', 'Empresa'),]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='clients')
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    phone = models.CharField(max_length=50)
    email = models.EmailField(blank=True, null=True)
    address = models.TextField(blank=True)

    def __str__(self):
        return self.name

class Batch(LifeCycle):
    STATUS_CHOICES = [
        ('active', 'Ativo'),
        ('completed', 'Concluído'),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='batches')
    name = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)
    initial_chicken_count = models.PositiveIntegerField()
    current_chicken_count = models.PositiveIntegerField()
    frozen_count = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    notes = models.TextField(blank=True)

    def __str__(self):
        return self.name

    @property
    def live_count(self):
        """Frangos vivos = disponíveis - congelados"""
        return self.current_chicken_count - self.frozen_count

    @property
    def total_expenses(self):
        return self.expenses.aggregate(total=models.Sum('total'))['total'] or Decimal('0.00')

    @property
    def total_sales(self):
        return self.sales.filter(payment_status='paid').aggregate(total=models.Sum('total'))['total'] or Decimal('0.00')

    @property
    def profit(self):
        return self.total_sales - self.total_expenses

    def clean(self):
        if self.frozen_count > self.current_chicken_count:
            raise ValidationError("Quantidade congelada não pode exceder o total disponível.")
        if self.status == 'completed' and not self.end_date:
            self.end_date = timezone.now().date()

    def save(self, *args, **kwargs):
        if not self.pk:  # novo lote
            self.current_chicken_count = self.initial_chicken_count
        self.full_clean()
        super().save(*args, **kwargs)

class Expense(LifeCycle):
    CATEGORY_CHOICES = [
        ('chickens', 'Pintainhos'),
        ('feed', 'Ração'),
        ('medicine', 'Medicamentos'),
        ('transport', 'Transporte'),
        ('labor', 'Mão de obra'),
        ('equipment', 'Equipamento'),
        ('other', 'Outro'),
    ]
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name='expenses')
    description = models.CharField(max_length=255)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    total = models.DecimalField(max_digits=12, decimal_places=2, editable=False)

    def save(self, *args, **kwargs):
        self.total = self.quantity * self.unit_price
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.description} - {self.total} Kz"

class Loss(LifeCycle):
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name='losses')
    quantity = models.PositiveIntegerField()
    reason = models.CharField(max_length=255)
    date = models.DateField(default=timezone.now)

    def clean(self):
        if self.quantity > self.batch.live_count:
            raise ValidationError("Quantidade de perda excede os frangos vivos disponíveis.")

    def save(self, *args, **kwargs):
        self.full_clean()
        is_new = not self.pk
        if is_new:
            self.batch.current_chicken_count -= self.quantity
            self.batch.save(update_fields=['current_chicken_count'])
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Perda de {self.quantity} frangos em {self.date}"

class Sale(LifeCycle):
    SALE_TYPE_CHOICES = [
        ('frozen', 'Congelado'),
        ('live', 'Vivo'),
    ]
    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Numerário'),
        ('mpesa', 'M-Pesa'),
        ('emola', 'e-Mola'),
    ]
    PAYMENT_STATUS_CHOICES = [
        ('paid', 'Pago'),
        ('pending', 'Pendente'),
    ]
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name='sales')
    client = models.ForeignKey(Client, on_delete=models.PROTECT, related_name='sales')
    sale_type = models.CharField(max_length=10, choices=SALE_TYPE_CHOICES)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    total = models.DecimalField(max_digits=12, decimal_places=2, editable=False)
    payment_method = models.CharField(max_length=10, choices=PAYMENT_METHOD_CHOICES)
    payment_status = models.CharField(max_length=10, choices=PAYMENT_STATUS_CHOICES, default='paid')
    payment_due_date = models.DateField(blank=True, null=True)
    paid_date = models.DateField(blank=True, null=True)
    date = models.DateField(default=timezone.now)
    notes = models.TextField(blank=True)

    def clean(self):
        # Validação de estoque
        if self.sale_type == 'frozen':
            if self.quantity > self.batch.frozen_count:
                raise ValidationError(f"Quantidade insuficiente de frangos congelados. Disponível: {self.batch.frozen_count}")
        else:  # live
            if self.quantity > self.batch.live_count:
                raise ValidationError(f"Quantidade insuficiente de frangos vivos. Disponível: {self.batch.live_count}")

        if self.payment_status == 'pending' and not self.payment_due_date:
            raise ValidationError("Data prevista de pagamento é obrigatória para vendas pendentes.")
        if self.payment_status == 'paid' and not self.paid_date:
            self.paid_date = timezone.now().date()

    def save(self, *args, **kwargs):
        self.total = self.quantity * self.unit_price
        self.full_clean()
        is_new = not self.pk
        if is_new:
            # Atualizar inventário
            if self.sale_type == 'frozen':
                self.batch.frozen_count -= self.quantity
                self.batch.current_chicken_count -= self.quantity
            else:  # live
                self.batch.current_chicken_count -= self.quantity
            self.batch.save(update_fields=['frozen_count', 'current_chicken_count'])
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Venda {self.id} - {self.client.name} - {self.total} Kz"
    