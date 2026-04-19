import django_filters
from apps.apartments.models import Building
from apps.issues.models import Category, Issue
from django.db.models import Q
from django.utils import timezone


class IssueFilter(django_filters.FilterSet):
    status = django_filters.ChoiceFilter(choices=Issue.IssueStatus.choices)
    priority = django_filters.ChoiceFilter(choices=Issue.Priority.choices)
    category = django_filters.ModelChoiceFilter(queryset=Category.objects.all())
    building = django_filters.ModelChoiceFilter(
        queryset=Building.objects.all(),
        field_name="unit__entrance__building",
        label="Building",
    )
    is_overdue = django_filters.BooleanFilter(method="filter_is_overdue", label="Overdue")

    def filter_is_overdue(self, queryset, name, value):
        now = timezone.now()
        terminal = (Issue.IssueStatus.DONE, Issue.IssueStatus.REJECTED)
        overdue_q = Q(due_at__lt=now) & ~Q(status__in=terminal)
        if value:
            return queryset.filter(overdue_q)
        return queryset.exclude(overdue_q)

    class Meta:
        model = Issue
        fields = ["status", "priority", "category", "building"]
