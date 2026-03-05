from django.contrib import admin

from apps.passes.models import VehiclePass


@admin.register(VehiclePass)
class VehiclePassAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "tenant",
        "unit",
        "get_building",
        "car_number",
        "visit_date",
        "status",
        "closed_by",
        "closed_at",
    ]
    list_filter = ["status", "visit_date", "unit__entrance__building"]
    search_fields = [
        "tenant__username",
        "tenant__first_name",
        "tenant__last_name",
        "car_number",
    ]
    readonly_fields = ["closed_at", "created_at", "updated_at"]
    date_hierarchy = "visit_date"

    @admin.display(description="Building")
    def get_building(self, obj):
        if obj.unit and obj.unit.entrance:
            return obj.unit.entrance.building.name
        return "—"
