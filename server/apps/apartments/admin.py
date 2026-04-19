# Imports
from apps.apartments.models import Building, Entrance, Unit
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


@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    # PR-7 dropped the ``apartment`` column from ``list_display`` along
    # with the legacy Apartment model.
    list_display = ["id", "number", "floor", "entrance"]
    list_filter = ["entrance__building"]
    search_fields = ["number", "entrance__building__name"]
    autocomplete_fields = ["entrance"]
