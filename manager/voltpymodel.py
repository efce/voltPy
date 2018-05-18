from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import m2m_changed
from overrides import overrides
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
        user = manager.helpers.functions.get_user()
        if self.id is None:
            # it is new object in DB, so user is owner
            self.owner = user
            super().save()
            if user is not None:
                assign_perm('rw', user, self)
                assign_perm('del', user, self)
            return
        if user.has_perm('rw', self):
            super().save()
        else:
            raise VoltPyNotAllowed('Operation not allowed.')

    @classmethod
    def get(cls, *args, **kwargs):
        user = manager.helpers.functions.get_user()
        kwargs['deleted'] = False
        perms = ('rw', 'ro')
        try:
            return get_objects_for_user(user, perms, klass=cls, any_perm=True).get(*args, **kwargs)
        except:
            raise VoltPyDoesNotExists('Object does not exists.')

    @classmethod
    def filter(cls, *args, **kwargs):
        user = manager.helpers.functions.get_user()
        kwargs['deleted'] = False
        perms = ('rw', 'ro')
        try:
            return get_objects_for_user(user, perms, klass=cls, any_perm=True).filter(*args, **kwargs)
        except:
            raise VoltPyDoesNotExists('Object does not exists.')

    @classmethod
    def all(cls, *args, **kwargs):
        user = manager.helpers.functions.get_user()
        perms = ('rw', 'ro')
        return get_objects_for_user(user, perms, klass=cls, any_perm=True).filter(deleted=False)

    def delete(self):
        user = manager.helpers.functions.get_user()
        if user.has_perm('del', self):
            self.deleted = True
            super().save()
        else:
            raise VoltPyNotAllowed('Operation not allowed.')


def check_permission(sender, instance, **kwargs):
    if not isinstance(instance, VoltPyModel):
        return
    user = manager.helpers.functions.get_user()
    if not user.has_perm('rw', instance):
        raise VoltPyNotAllowed('Operation not allowed.')
m2m_changed.connect(check_permission, sender=None)
