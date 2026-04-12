import logging
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)

# Cache for old issue statuses before save
_issue_old_status: dict = {}
_issue_old_assigned_to: dict = {}


# Use actual model classes (not strings) so that signal.disconnect() works
# reliably in seed_demo and other management commands.
def _get_issue_model():
    from apps.issues.models import Issue
    return Issue


def _get_vehicle_pass_model():
    from apps.passes.models import VehiclePass
    return VehiclePass


def _get_announcement_model():
    from apps.posts.models import Announcement
    return Announcement


# We still need to register with string senders so Django can resolve the
# models lazily at startup (avoids circular-import issues during AppConfig.ready).
# But we also register a connect-on-ready callback so that disconnect() with
# the actual model class works correctly.

@receiver(pre_save, sender="issues.Issue")
def cache_issue_old_state(sender, instance, **kwargs):
    """Cache old status and assigned_to before saving."""
    if instance.pk:
        try:
            old = sender.objects.get(pk=instance.pk)
            _issue_old_status[str(instance.pk)] = old.status
            _issue_old_assigned_to[str(instance.pk)] = old.assigned_to_id
        except sender.DoesNotExist:
            pass


@receiver(post_save, sender="issues.Issue")
def on_issue_saved(sender, instance, created, **kwargs):
    """Trigger notifications after Issue is saved."""
    from apps.notifications.tasks import (
        notify_dispatchers_new_issue,
        notify_tenant_issue_status_changed,
        notify_worker_assigned,
    )

    pk_str = str(instance.pk)

    if created:
        notify_dispatchers_new_issue.delay(str(instance.pk))
        return

    old_status = _issue_old_status.pop(pk_str, None)
    old_assigned = _issue_old_assigned_to.pop(pk_str, None)

    if old_status and old_status != instance.status:
        notify_tenant_issue_status_changed.delay(
            str(instance.pk), old_status, instance.status
        )

    if old_assigned != instance.assigned_to_id and instance.assigned_to_id:
        notify_worker_assigned.delay(str(instance.pk))


@receiver(post_save, sender="passes.VehiclePass")
def on_pass_saved(sender, instance, created, **kwargs):
    """Notify tenant when pass is closed."""
    if not created and instance.status == "closed":
        from apps.notifications.tasks import notify_tenant_pass_status
        notify_tenant_pass_status.delay(str(instance.pk), instance.status)


@receiver(post_save, sender="posts.Announcement")
def on_announcement_created(sender, instance, created, **kwargs):
    """Notify all tenants when new announcement is published."""
    if created:
        from apps.notifications.tasks import notify_building_tenants_announcement
        notify_building_tenants_announcement.delay(str(instance.pk))


def connect_all():
    """
    Re-connect all signals using the resolved model classes.
    Called from NotificationsConfig.ready() AFTER the app registry is loaded.
    This ensures that disconnect(sender=ModelClass) works correctly
    (e.g. in seed_demo and other management commands).
    """
    from apps.issues.models import Issue
    from apps.passes.models import VehiclePass
    from apps.posts.models import Announcement

    # Connect with actual classes (disconnect() will work with these)
    pre_save.connect(cache_issue_old_state, sender=Issue, weak=False)
    post_save.connect(on_issue_saved, sender=Issue, weak=False)
    post_save.connect(on_pass_saved, sender=VehiclePass, weak=False)
    post_save.connect(on_announcement_created, sender=Announcement, weak=False)
