from rest_framework import permissions

class IsOwner(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        # Para modelos que têm relação com user (Batch, Client)
        if hasattr(obj, 'user'):
            return obj.user == request.user
        # Para modelos relacionados via batch (Expense, Loss, Sale)
        if hasattr(obj, 'batch'):
            return obj.batch.user == request.user
        return False