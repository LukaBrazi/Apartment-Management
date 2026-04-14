# Imports
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.organizations.features import DEFAULT_FEATURES
from apps.organizations.models import Organization


# ── Set Default Features Signal ────────────────────────────────────────────────

@receiver(post_save, sender=Organization)
def set_default_features(sender, instance, created, **kwargs):
    """Set default features for new organizations.

    Сигнал для встановлення функцій за замовчуванням для нових організацій.

    Args:
        sender: Модель, яка відправляє сигнал.
        instance (Organization): Екземпляр організації.
        created (bool): True якщо організація щойно створена.
        **kwargs: Додаткові аргументи.
    """
    if created and not instance.features:
        instance.features = DEFAULT_FEATURES.copy()
        instance.save(update_fields=["features"])
