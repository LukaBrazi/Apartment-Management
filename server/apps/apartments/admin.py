# Imports
from apps.apartments.models import Apartment, Building, Entrance, ResidentialComplex, Unit
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
    list_display = ["id", "number", "floor", "entrance", "apartment"]
    list_filter = ["entrance__building"]
    search_fields = ["number", "entrance__building__name"]
    autocomplete_fields = ["entrance"]


# Register the Apartment model with the admin panel
@admin.register(Apartment)
class ApartmentAdmin(admin.ModelAdmin):
    """ApartmentAdmin

    ApartmentAdmin class is used to customize the admin panel for the Apartment model.

    Extends:
        admin.ModelAdmin

    Attributes:
        list_display (list): A list of fields to display in the admin panel.
        list_display_links (list): A list of fields to link to the detail page.
        list_filter (list): A list of fields to filter by.
        search_fields (list): A list of fields to search by.
        ordering (list): A list of fields to order by.
        autocomplete_fields (list): A list of fields to autocomplete.
    """

    # Attributes
    list_display = ["id", "unit_number", "building", "floor", "tenant"]
    list_display_links = ["id", "unit_number"]
    list_filter = ["building", "floor"]
    search_fields = ["unit_number", "building", "floor"]
    ordering = ["building", "floor"]
    autocomplete_fields = ["tenant"]
