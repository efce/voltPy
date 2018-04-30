from django.db import models
from manager.exceptions import VoltPyNotAllowed
import manager


class VoltPyModel(models.Model):
    id = models.AutoField(primary_key=True)
    deleted = models.BooleanField(default=False)

    class Meta:
        abstract = True

    def save(self):
        if self.id is None:
            super().save()
            return
        user = manager.helpers.functions.getUser()
        if user.has_perm('rw', self):
            super().save()
        else:
            raise VoltPyNotAllowed('Operation not allowed.')

    def get(self, *args, **kwargs):
        user = manager.helpers.functions.getUser()
        if user.has_perm('ro', self):
            kwargs['deleted'] = False
            self.objects.get(*args, **kwargs)
        else:
            raise VoltPyNotAllowed('Operation not allowed.')

    def filter(self, *args, **kwargs):
        user = manager.helpers.functions.getUser()
        if user.has_perm('ro', self):
            kwargs['deleted'] = False
            self.objects.filter(*args, **kwargs)
        else:
            raise VoltPyNotAllowed('Operation not allowed.')

    def delete(self):
        user = manager.helpers.functions.getUser()
        if user.has_perm('del', self):
            self.deleted = True
            super().save()
        else:
            raise VoltPyNotAllowed('Operation not allowed.')
