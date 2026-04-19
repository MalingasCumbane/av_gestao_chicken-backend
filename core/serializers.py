from rest_framework import serializers
from .models import Batch, Client, Expense, Loss, Sale
from django.utils import timezone

class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = '__all__'
        read_only_fields = ('id', 'user', 'created_at', 'updated_at')

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

# class ExpenseSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Expense
#         fields = '__all__'
#         read_only_fields = ('id', 'total', 'created_at', 'updated_at')


# core/serializers.py
class ExpenseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Expense
        fields = ['id', 'batch', 'description', 'category', 'quantity', 'unit_price', 'total', 'created_at', 'updated_at']
        read_only_fields = ['id', 'batch', 'total', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        # O batch é passado via contexto ou perform_create
        batch = self.context.get('batch')
        if batch:
            validated_data['batch'] = batch
        return super().create(validated_data)


# class LossSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Loss
#         fields = '__all__'
#         read_only_fields = ('id', 'created_at', 'updated_at')

#     def validate(self, data):
#         batch = data['batch']
#         quantity = data['quantity']
#         if quantity > batch.live_count:
#             raise serializers.ValidationError(f"Perda excede frangos vivos disponíveis ({batch.live_count}).")
#         return data

class LossSerializer(serializers.ModelSerializer):
    class Meta:
        model = Loss
        fields = ['id', 'batch', 'quantity', 'reason', 'date', 'created_at', 'updated_at']
        read_only_fields = ['id', 'batch', 'created_at', 'updated_at']

    def to_representation(self, instance):
        """Garante que o formato corresponda ao mockData"""
        return {
            'id': str(instance.id),
            'quantity': instance.quantity,
            'reason': instance.reason,
            'date': instance.date.isoformat() if instance.date else None,
        }

    def validate_quantity(self, value):
        batch = self.context.get('batch')
        if batch and value > batch.live_count:
            raise serializers.ValidationError(
                f"Quantidade de perda ({value}) excede os frangos vivos disponíveis ({batch.live_count})."
            )
        return value



class SaleSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source='client.name', read_only=True)
    batch_name = serializers.CharField(source='batch.name', read_only=True)

    class Meta:
        model = Sale
        fields = '__all__'
        read_only_fields = ('id', 'total', 'created_at', 'updated_at', 'paid_date')

    def validate(self, data):
        batch = data['batch']
        sale_type = data['sale_type']
        quantity = data['quantity']

        if sale_type == 'frozen' and quantity > batch.frozen_count:
            raise serializers.ValidationError(f"Estoque congelado insuficiente. Disponível: {batch.frozen_count}")
        if sale_type == 'live' and quantity > batch.live_count:
            raise serializers.ValidationError(f"Estoque vivo insuficiente. Disponível: {batch.live_count}")

        if data.get('payment_status') == 'pending' and not data.get('payment_due_date'):
            raise serializers.ValidationError("Data prevista é obrigatória para pagamento pendente.")
        return data

# class BatchListSerializer(serializers.ModelSerializer):
#     live_count = serializers.IntegerField(read_only=True)
#     total_expenses = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
#     total_sales = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
#     profit = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

#     class Meta:
#         model = Batch
#         fields = [
#             'id', 'name', 'start_date', 'end_date', 'initial_chicken_count',
#             'current_chicken_count', 'frozen_count', 'live_count', 'status',
#             'total_expenses', 'total_sales', 'profit', 'created_at', 'updated_at'
#         ]
#         read_only_fields = ('id', 'user', 'current_chicken_count', 'frozen_count', 'created_at', 'updated_at')

class BatchListSerializer(serializers.ModelSerializer):
    # Mapear para os nomes esperados pelo frontend
    currentChickenCount = serializers.IntegerField(source='current_chicken_count', read_only=True)
    frozenCount = serializers.IntegerField(source='frozen_count', read_only=True)
    initial_chicken_count = serializers.IntegerField(read_only=True)
    start_date = serializers.DateField(read_only=True)
    endDate = serializers.DateField(source='end_date', read_only=True, allow_null=True)
    
    # Propriedades calculadas
    live_count = serializers.IntegerField(read_only=True)
    total_expenses = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    total_sales = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    profit = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    
    # 🔥 LISTA DE LOSSES COMPLETA
    losses = LossSerializer(many=True, read_only=True)
    
    # Opcional: Incluir também expenses e sales se quiser tudo de uma vez
    # expenses = ExpenseSerializer(many=True, read_only=True)
    # sales = SaleSerializer(many=True, read_only=True)

    class Meta:
        model = Batch
        fields = [
            'id', 'name', 'start_date', 'endDate', 'initial_chicken_count',
            'currentChickenCount', 'frozenCount', 'live_count', 'status',
            'total_expenses', 'total_sales', 'profit', 
            'losses', 'expenses', 'sales',  # 🔥 Listas completas
            'notes', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'currentChickenCount', 'frozenCount', 'created_at', 'updated_at']

    def to_representation(self, instance):
        """Garante que o formato corresponda exatamente ao mockData"""
        return {
            'id': str(instance.id),
            'name': instance.name,
            'start_date': instance.start_date.isoformat() if instance.start_date else None,
            'end_date': instance.end_date.isoformat() if instance.end_date else None,
            'initial_chicken_count': instance.initial_chicken_count,
            'current_chicken_count': instance.current_chicken_count,
            'frozen_count': instance.frozen_count,
            'status': instance.status,
            'notes': instance.notes,
            'live_count': instance.live_count,
            'total_expenses': float(instance.total_expenses),
            'total_sales': float(instance.total_sales),
            'profit': float(instance.profit),
            'losses': LossSerializer(instance.losses.all(), many=True).data,
            'expenses': ExpenseSerializer(instance.expenses.all(), many=True).data,
            'sales': SaleSerializer(instance.sales.all(), many=True).data,
            'created_at': instance.created_at.isoformat() if instance.created_at else None,
            'updated_at': instance.updated_at.isoformat() if instance.updated_at else None,
        }


class BatchDetailSerializer(BatchListSerializer):
    # Herda tudo do BatchListSerializer, já que ele já inclui todas as listas
    pass

# class BatchDetailSerializer(BatchListSerializer):
#     expenses = ExpenseSerializer(many=True, read_only=True)
#     losses = LossSerializer(many=True, read_only=True)
#     sales = SaleSerializer(many=True, read_only=True)

#     class Meta(BatchListSerializer.Meta):
#         fields = BatchListSerializer.Meta.fields + ['expenses', 'losses', 'sales', 'notes']

class BatchCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Batch
        fields = ['name', 'start_date', 'initial_chicken_count', 'notes']
        # current_chicken_count e frozen_count são gerenciados automaticamente

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

class SlaughterSerializer(serializers.Serializer):
    quantity = serializers.IntegerField(min_value=1)

    def validate_quantity(self, value):
        batch = self.context['batch']
        if value > batch.live_count:
            raise serializers.ValidationError(f"Quantidade excede frangos vivos ({batch.live_count}).")
        return value

class PaymentConfirmationSerializer(serializers.Serializer):
    paid_date = serializers.DateField(required=False, default=timezone.now().date())