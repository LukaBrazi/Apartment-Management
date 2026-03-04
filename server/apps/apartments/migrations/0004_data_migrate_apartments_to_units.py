"""
Data migration: populate Building / Entrance / Unit from existing Apartment records.

Strategy:
- Each unique Apartment.building (CharField) → 1 Building
- Each Building gets 1 default Entrance ("1")
- Each Apartment → 1 Unit linked back via Unit.apartment OneToOne
"""
from django.db import migrations


def forward_migrate(apps, schema_editor):
    Apartment = apps.get_model("apartments", "Apartment")
    Building = apps.get_model("apartments", "Building")
    Entrance = apps.get_model("apartments", "Entrance")
    Unit = apps.get_model("apartments", "Unit")

    if not Apartment.objects.exists():
        # Nothing to migrate
        return

    # Group apartments by their building name
    building_names = Apartment.objects.values_list("building", flat=True).distinct()

    for building_name in building_names:
        building, _ = Building.objects.get_or_create(
            name=building_name,
            defaults={"address": building_name, "city": ""},
        )
        entrance, _ = Entrance.objects.get_or_create(
            building=building,
            name="1",
        )
        apartments = Apartment.objects.filter(building=building_name)
        for apt in apartments:
            # Skip if Unit already exists for this apartment
            if Unit.objects.filter(apartment_id=apt.pk).exists():
                continue
            Unit.objects.create(
                entrance=entrance,
                number=apt.unit_number,
                floor=apt.floor,
                apartment_id=apt.pk,
            )


def reverse_migrate(apps, schema_editor):
    Unit = apps.get_model("apartments", "Unit")
    Entrance = apps.get_model("apartments", "Entrance")
    Building = apps.get_model("apartments", "Building")
    # Only remove records that were created by this migration
    Unit.objects.filter(apartment__isnull=False).delete()
    # Remove entrances/buildings that now have no units
    for entrance in Entrance.objects.all():
        if not entrance.units.exists():
            entrance.delete()
    for building in Building.objects.all():
        if not building.entrances.exists():
            building.delete()


class Migration(migrations.Migration):

    dependencies = [
        ("apartments", "0003_add_building_entrance_unit"),
    ]

    operations = [
        migrations.RunPython(forward_migrate, reverse_migrate),
    ]
