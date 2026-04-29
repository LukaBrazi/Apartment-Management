# Imports
from collections import Counter

from apps.apartments.models import Building, Entrance, Unit
from django.db import IntegrityError, transaction
from rest_framework import serializers


# ── Domain serializers ─────────────────────────────────────────────────────


class EntranceWriteSerializer(serializers.Serializer):
    """Write-only nested payload for ``BuildingSerializer.entrances``.

    Used only on the create path — the read shape of an entrance lives
    in ``EntranceSerializer`` / ``EntranceDetailSerializer``.

    Caps:
    * ``name`` — 1..20 chars (matches ``Entrance.name`` ``max_length=20``).
    * ``apartments_count`` — 1..500 (operational sanity limit; a bigger
      number creates >10 000 rows for a 20-entrance building).
    """

    name = serializers.CharField(min_length=1, max_length=20)
    apartments_count = serializers.IntegerField(min_value=1, max_value=500)


class BuildingSerializer(serializers.ModelSerializer):
    """Read+write serializer for buildings.

    ``organization`` is **not** in ``Meta.fields`` — it is assigned by
    ``perform_create`` on the view (see PR-14 Bug 1 fix).  Allowing the
    client to write it would let any staff caller spoof the FK and
    park a building under another tenant.  Lock-down regex tests in
    ``apps/apartments/tests/test_admin_view_lockdowns.py`` enforce this.

    ``entrances`` is a write-only nested payload that, when present,
    seeds the entrance + unit rows in the same atomic transaction as
    the building itself.  Read responses do not include this field —
    the entrances/units are exposed via their dedicated endpoints.
    """

    pkid = serializers.IntegerField(read_only=True)
    organization_name = serializers.ReadOnlyField(source="organization.name")
    entrances = serializers.ListField(
        child=EntranceWriteSerializer(),
        write_only=True,
        required=False,
        default=list,
        max_length=20,
    )

    class Meta:
        model = Building
        fields = [
            "pkid",
            "id",
            "name",
            "address",
            "city",
            "is_active",
            "organization_name",
            "created_at",
            "entrances",
        ]

    def validate_entrances(self, value):
        """Reject duplicate entrance names within the same payload.

        The DB also enforces ``unique_together = (building, name)``, but
        catching the duplicate at the serializer layer gives the client
        a sane field-scoped error message instead of a generic
        ``IntegrityError``.
        """
        if not value:
            return value
        names = [e["name"] for e in value]
        dups = [n for n, count in Counter(names).items() if count > 1]
        if dups:
            raise serializers.ValidationError(
                f"Дублювання імен підʼїздів: {', '.join(sorted(dups))}"
            )
        return value

    def create(self, validated_data):
        entrances_data = validated_data.pop("entrances", [])
        try:
            with transaction.atomic():
                building = Building.objects.create(**validated_data)
                for entrance_payload in entrances_data:
                    entrance = Entrance.objects.create(
                        building=building,
                        name=entrance_payload["name"],
                        # Defensive: explicitly pin org so the FK is set
                        # even if Entrance.save() short-circuits on a
                        # half-built building (the .save() override on
                        # Entrance only runs the auto-fill once).
                        organization=building.organization,
                    )
                    apartments_count = entrance_payload["apartments_count"]
                    units = [
                        Unit(
                            entrance=entrance,
                            number=str(n),
                            organization=building.organization,
                        )
                        for n in range(1, apartments_count + 1)
                    ]
                    # bulk_create is ~10x faster than per-row save() for
                    # the 500-unit case and avoids the per-row save()
                    # signal overhead.  ``Unit.save()``'s org auto-fill
                    # is skipped, but we set it explicitly above.
                    Unit.objects.bulk_create(units)
        except IntegrityError as exc:
            # Safety net — DB-level unique violation on (building, name)
            # somehow slipped past validate_entrances.
            raise serializers.ValidationError(
                {"entrances": f"Конфлікт даних при створенні підʼїздів: {exc}"}
            ) from exc
        return building


class EntranceSerializer(serializers.ModelSerializer):
    building_name = serializers.ReadOnlyField(source="building.name")

    class Meta:
        model = Entrance
        fields = ["id", "building", "building_name", "name", "created_at"]


class EntranceDetailSerializer(serializers.ModelSerializer):
    """Admin-side detail serializer for entrance management.

    Adds ``units_count`` so the frontend modal can show
    "Підʼїзд А — 12 квартир" without a second round-trip.
    """

    building_name = serializers.ReadOnlyField(source="building.name")
    units_count = serializers.SerializerMethodField()

    class Meta:
        model = Entrance
        fields = [
            "id",
            "building",
            "building_name",
            "name",
            "units_count",
            "created_at",
        ]
        read_only_fields = ["id", "building", "building_name", "created_at"]

    def get_units_count(self, obj) -> int:
        return obj.units.count()


class UnitSerializer(serializers.ModelSerializer):
    entrance_name = serializers.ReadOnlyField(source="entrance.name")
    building_name = serializers.ReadOnlyField(source="entrance.building.name")
    # Alias: unit_id == id (stable API name going forward).  Must use
    # ``UUIDField`` (not ``ReadOnlyField``) to coerce the value to a
    # string — the custom ``GenericJSONRenderer`` calls ``json.dumps``
    # directly and would otherwise choke on a raw ``UUID`` object.
    unit_id = serializers.UUIDField(source="id", read_only=True)

    class Meta:
        model = Unit
        fields = [
            "id",
            "unit_id",
            "number",
            "floor",
            "entrance",
            "entrance_name",
            "building_name",
            "created_at",
        ]
