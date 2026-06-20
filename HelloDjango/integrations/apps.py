from django.apps import AppConfig


class IntegrationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'integrations'
    verbose_name = 'Интеграции с МИС'

    def ready(self):
        # подключаем сигналы (post_save на Appointment → push в МИС)
        from . import signals  # noqa: F401
