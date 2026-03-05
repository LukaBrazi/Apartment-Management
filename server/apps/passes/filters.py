import django_filters

from apps.passes.models import VehiclePass


class VehiclePassFilter(django_filters.FilterSet):
    visit_date = django_filters.DateFilter(field_name="visit_date")
    building = django_filters.NumberFilter(
        field_name="unit__entrance__building__pkid"
    )
    tenant = django_filters.CharFilter(
        field_name="tenant__username", lookup_expr="icontains"
    )

    class Meta:
        model = VehiclePass
        fields = ["visit_date", "building", "tenant", "status"]
