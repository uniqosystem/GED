from django.apps import AppConfig


class TramitacaoConfig(AppConfig):
    name = 'tramitacao'

    def ready(self):
        from . import signals  # noqa: F401
