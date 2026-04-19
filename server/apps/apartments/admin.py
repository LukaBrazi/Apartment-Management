# Imports
from apps.apartments.models import Building, Entrance, Residency, Unit
from django.contrib import admin


@admin.register(Building)
class BuildingAdmin(admin.ModelAdmin):
    # PR-8: ``complex`` column removed along with the ``ResidentialComplex``
    # model.  Buildings are now scoped to ``organization`` exclusively.
    list_display = ["id", "name", "address", "city", "organization", "is_active", "created_at"]
    list_filter = ["is_active", "city", "organization"]
    search_fields = ["name", "address"]
    autocomplete_fields = ["organization"]


@admin.register(Entrance)
class EntranceAdmin(admin.ModelAdmin):
    list_display = ["id", "building", "name", "created_at"]
    list_filter = ["building"]
    search_fields = ["name", "building__name"]
    autocomplete_fields = ["building"]


class ResidencyInline(admin.TabularInline):
    """Residents living in a ``Unit`` — shown on the unit-edit page.

    Gives HOA admins / superadmins an immediate view of who owns or
    rents the apartment and which residency is primary.  Inline is
    read-friendly (``autocomplete_fields`` on ``user``) and keeps
    ``extra=0`` so the page doesn't open with a blank form.
    """

    model = Residency
    extra = 0
    fields = ["user", "role", "is_primary", "start_date", "end_date"]
    autocomplete_fields = ["user"]
    show_change_link = True


@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    # PR-7 dropped the ``apartment`` column from ``list_display`` along
    # with the legacy Apartment model.
    list_display = ["id", "number", "floor", "entrance", "primary_resident_display"]
    list_filter = ["entrance__building"]
    search_fields = ["number", "entrance__building__name"]
    autocomplete_fields = ["entrance"]
    inlines = [ResidencyInline]

    @admin.display(description="Primary resident")
    def primary_resident_display(self, obj: Unit) -> str:
        """Show the primary residency on the unit list page (if any)."""
        primary = obj.residencies.filter(is_primary=True).select_related("user").first()
        if primary is None:
            return "—"
        return f"{primary.user} ({primary.get_role_display()})"


@admin.register(Residency)
class ResidencyAdmin(admin.ModelAdmin):
    """Standalone admin for ``Residency`` — lets admins search across
    all user × unit relationships without having to drill into a Unit.
    """

    list_display = [
        "id",
        "user",
        "unit",
        "role",
        "is_primary",
        "start_date",
        "end_date",
    ]
    list_filter = ["role", "is_primary", "unit__entrance__building"]
    search_fields = [
        "user__username",
        "user__email",
        "user__first_name",
        "user__last_name",
        "unit__number",
        "unit__entrance__building__name",
    ]
    autocomplete_fields = ["user", "unit"]
