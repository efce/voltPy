from django.db import models
from django.contrib.auth.models import User
from guardian.shortcuts import assign_perm
from guardian.shortcuts import get_objects_for_user
from manager.exceptions import VoltPyNotAllowed
from manager.exceptions import VoltPyDoesNotExists
import manager


class VoltPyModel(models.Model):
    id = models.AutoField(primary_key=True)
    owner = models.ForeignKey(User, on_delete=models.DO_NOTHING)
    deleted = models.BooleanField(default=False)

    class Meta:
        abstract = True

    def save(self):
        user = manager.helpers.functions.getUser()
        if self.id is None:
            # it is new object in DB, so user is owner
            self.owner = user
            super().save()
            if user is not None:
                assign_perm('rw', user, self)
            return
        if user.has_perm('rw', self):
            super().save()
        else:
            raise VoltPyNotAllowed('Operation not allowed.')

    @classmethod
    def get(cls, *args, **kwargs):
        user = manager.helpers.functions.getUser()
        kwargs['deleted'] = False
        perms = ('rw', 'ro')
        try:
            return get_objects_for_user(user, perms, klass=cls, any_perm=True).get(*args, **kwargs)
        except:
            raise VoltPyDoesNotExists('Object does not exists.')
            

    @classmethod
    def filter(cls, *args, **kwargs):
        user = manager.helpers.functions.getUser()
        kwargs['deleted'] = False
        perms = ('rw', 'ro')
        try:
            return get_objects_for_user(user, perms, klass=cls, any_perm=True).filter(*args, **kwargs)
        except:
            raise VoltPyDoesNotExists('Object does not exists.')

    @classmethod
    def all(cls, *args, **kwargs):
        user = manager.helpers.functions.getUser()
        kwargs['deleted'] = False
        perms = ('rw', 'ro')
        return get_objects_for_user(user, perms, klass=cls, any_perm=True)

    def delete(self):
        user = manager.helpers.functions.getUser()
        if user.has_perm('del', self):
            self.deleted = True
            super().save()
        else:
            raise VoltPyNotAllowed('Operation not allowed.')
