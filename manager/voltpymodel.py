from django.db import models
from manager.exceptions import VoltPyNotAllowed
import manager


#  W HUJ NIE DIZALA
class VoltPyModel(models.Model):
    id = models.AutoField(primary_key=True)

    class Meta:
        permissions = (
            ('ro', 'Read only'),
            ('rw', 'Read write'),
            ('del', 'Delete'),
        )

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
            self.objects.get(*args, **kwargs)
        else:
            raise VoltPyNotAllowed('Operation not allowed.')

    def filter(self, *args, **kwargs):
        user = manager.helpers.functions.getUser()
        if user.has_perm('ro', self):
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
