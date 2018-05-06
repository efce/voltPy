from django.contrib.auth.models import Group
from django.db.models.signals import post_migrate
from django.dispatch import receiver

@receiver(post_migrate)
def migration_db_upgrade( **kwargs):
    existing_groups = []
    if not Group.objects.filter(name='all_users').exists():
        group = Group(name='all_users')
        group.save()
    if not Group.objects.filter(name='temp_users').exists():
        group = Group(name='temp_users')
        group.save()
    if not Group.objects.filter(name='registered_users').exists():
        group = Group(name='registered_users')
        group.save()
    from django.contrib.sites.models import Site
    one = Site.objects.all()
    if one.exists():
        one = one[0]
        one.domain = 'voltammetry.center'
        one.name = 'Voltammetry Center'
        one.save()
    else:
        one = Site(
            domain='voltammetry.center',
            name='Voltammetry Center',
        )
        one.save()
