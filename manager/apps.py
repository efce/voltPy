from django.apps import AppConfig
from django.db.models.signals import post_migrate


class ManagerConfig(AppConfig):
    name = 'manager'
    
    def ready(self):
        from manager.signals import migration_db_upgrade
        post_migrate.connect(migration_db_upgrade)
