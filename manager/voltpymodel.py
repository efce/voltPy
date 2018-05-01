from django.db import models
from guardian.shortcuts import get_objects_for_user
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

    @classmethod
    def get(cls, *args, **kwargs):
        user = manager.helpers.functions.getUser()
        kwargs['deleted'] = False
        perms = ('rw', 'ro')
        return get_objects_for_user(user, perms, klass=cls, any_perm=True).get(*args, **kwargs)

    @classmethod
    def filter(cls, *args, **kwargs):
        user = manager.helpers.functions.getUser()
        kwargs['deleted'] = False
        perms = ('rw', 'ro')
        return get_objects_for_user(user, perms, klass=cls, any_perm=True).filter(*args, **kwargs)

    def delete(self):
        user = manager.helpers.functions.getUser()
        if user.has_perm('del', self):
            self.deleted = True
            super().save()
        else:
            raise VoltPyNotAllowed('Operation not allowed.')
