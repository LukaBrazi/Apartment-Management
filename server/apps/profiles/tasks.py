# Imports
from apps.profiles.models import Profile
from celery import shared_task


# Create a shared task to update all reputations
@shared_task(name="update_all_reputations")
def update_all_reputations() -> None:
    """Recompute and persist ``Profile.reputation`` for every profile.

    PR-6 — switched from a per-row ``profile.save()`` loop (which
    issued N UPDATE statements) to a single ``bulk_update`` call.
    The reputation formula lives on the model
    (``Profile.update_reputation``); we just call it in memory and
    flush the changes in one round trip.
    """

    profiles = list(Profile.objects.all())

    for profile in profiles:
        # In-memory mutation — does not hit the database.
        profile.update_reputation()

    if profiles:
        Profile.objects.bulk_update(profiles, fields=["reputation"], batch_size=200)
