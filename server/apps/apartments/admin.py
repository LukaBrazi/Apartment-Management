# Imports
from apps.apartments.models import Building, Entrance, ResidentialComplex, Unit
from django.contrib import admin


@admin.register(ResidentialComplex)
class ResidentialComplexAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "address", "city", "created_at"]
    search_fields = ["name", "address"]


@admin.register(Building)
class BuildingAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "address", "city", "complex", "is_active", "created_at"]
    list_filter = ["is_active", "city", "complex"]
    search_fields = ["name", "address"]
    autocomplete_fields = ["complex"]


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
