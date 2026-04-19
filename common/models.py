from django.db import models
from django_currentuser.middleware import (get_current_user, get_current_authenticated_user)
from django_currentuser.db.models import CurrentUserField


class Abstract(models.Model):
    active = models.BooleanField(("Activo"), default=True)
    delected = models.BooleanField(("Apagado"), default=False)

    def delete(self, *args, **kwargs):
        self.active = False
        self.delected = True
        super().save(*args, **kwargs)

    class Meta:
        abstract = True

class Code(Abstract):
    code = models.CharField(("Codigo"), max_length=50, unique=True)
    description = models.CharField(("Descriacao"), max_length=50, unique=True) 

    class Meta:
        abstract = True

    def __str__(self):
        return "{} {}".format(self.code)
    
class LifeCycle(Abstract):
    created_at = models.DateTimeField(("Criado em"), auto_now_add=True)
    updated_at = models.DateTimeField("Actualizado em", auto_now=True)
    created_by = CurrentUserField(related_name='created_%(class)ss')
    updated_by = CurrentUserField(related_name='updated_%(class)ss')

    class Meta:
        abstract = True


class LifeCycleCode(LifeCycle):
    code = models.CharField(("Codigo"), max_length=50, unique=True)
    description = models.CharField(("Descricao"), max_length=50)

    class Meta:
        abstract = True

    def __str__(self):
        return "{} {}".format(self.code, self.description)
    
    