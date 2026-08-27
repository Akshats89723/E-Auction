import os
from django.apps import AppConfig


class AuctionsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'auctions'

    def ready(self):
        # Guard: only start scheduler in the main process, not the reloader
        if os.environ.get('RUN_MAIN') != 'true':
            return
        from . import updater
        updater.start()
