from django.apps import AppConfig


class OrganizationsConfig(AppConfig):
    """Конфігурація додатку Organizations"""

    name = "apps.organizations"
    verbose_name = "Організації"

    def ready(self):
        """Готовність конфігурації додатку"""
        import apps.organizations.signals  # noqa
