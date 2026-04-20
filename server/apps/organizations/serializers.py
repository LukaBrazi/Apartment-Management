# Imports
from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.organizations.models import (
    Organization,
    OrganizationMembership,
    OrganizationType,
    OrgRole,
)

User = get_user_model()


# ── Organization Serializers ──────────────────────────────────────────────────

class OrganizationSerializer(serializers.ModelSerializer):
    """OrganizationSerializer

    Простий серіалізатор для організацій (список).

    Extends:
        serializers.ModelSerializer

    Meta Class:
        model (Organization): Модель Organization.
        fields (list): Поля для серіалізації.
    """

    owner_username = serializers.CharField(source="owner.username", read_only=True)

    class Meta:
        model = Organization
        fields = [
            "id",
            "pkid",
            "name",
            "slug",
            "type",
            "is_active",
            "features",
            "owner_username",
        ]


class OrganizationDetailSerializer(serializers.ModelSerializer):
    """OrganizationDetailSerializer

    Детальний серіалізатор для організацій.

    Extends:
        serializers.ModelSerializer

    Meta Class:
        model (Organization): Модель Organization.
        fields (list): Поля для серіалізації.
    """

    owner_username = serializers.CharField(source="owner.username", read_only=True)
    member_count = serializers.SerializerMethodField()

    class Meta:
        model = Organization
        fields = [
            "id",
            "name",
            "slug",
            "type",
            "owner_username",
            "features",
            "address",
            "city",
            "description",
            "phone",
            "email",
            "is_active",
            "member_count",
            "created_at",
            "updated_at",
        ]

    def get_member_count(self, obj) -> int:
        """Отримати кількість активних членів.

        Args:
            obj (Organization): Організація.

        Returns:
            int: Кількість активних членів.
        """
        return obj.memberships.filter(is_active=True).count()


class OrganizationCreateSerializer(serializers.ModelSerializer):
    """OrganizationCreateSerializer

    Серіалізатор для створення організацій.

    Extends:
        serializers.ModelSerializer

    Meta Class:
        model (Organization): Модель Organization.
        fields (list): Поля для серіалізації.
    """

    class Meta:
        model = Organization
        fields = [
            "name",
            "type",
            "address",
            "city",
        ]

    def create(self, validated_data):
        """Створити організацію з користувачем як власником.

        Args:
            validated_data (dict): Валідовані дані.

        Returns:
            Organization: Створена організація.
        """
        user = self.context["request"].user
        validated_data["owner"] = user
        return super().create(validated_data)


# ── Organization Membership Serializers ────────────────────────────────────────

class OrganizationMembershipSerializer(serializers.ModelSerializer):
    """OrganizationMembershipSerializer

    Серіалізатор для членства в організації.

    Extends:
        serializers.ModelSerializer

    Meta Class:
        model (OrganizationMembership): Модель OrganizationMembership.
        fields (list): Поля для серіалізації.
    """

    user_email = serializers.CharField(source="user.email", read_only=True)
    user_full_name = serializers.CharField(source="user.full_name", read_only=True)
    invited_by_name = serializers.CharField(
        source="invited_by.full_name", read_only=True
    )

    class Meta:
        model = OrganizationMembership
        fields = [
            "id",
            "user_email",
            "user_full_name",
            "organization",
            "role",
            "is_active",
            "staff_type",
            "joined_at",
            "invited_by_name",
        ]
        read_only_fields = [
            "id",
            "user_email",
            "user_full_name",
            "organization",
            "joined_at",
            "invited_by_name",
        ]


class AddMemberSerializer(serializers.Serializer):
    """AddMemberSerializer

    Серіалізатор для додавання членів в організацію.

    Extends:
        serializers.Serializer

    Attributes:
        user_email (EmailField): Email користувача.
        role (ChoiceField): Роль в організації.
        staff_type (CharField): Тип персоналу (опціонально).
    """

    user_email = serializers.EmailField()
    role = serializers.ChoiceField(choices=OrgRole.choices, default=OrgRole.RESIDENT)
    staff_type = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_user_email(self, value):
        """Перевірити, чи користувач існує.

        Args:
            value (str): Email користувача.

        Returns:
            str: Email користувача.

        Raises:
            serializers.ValidationError: Якщо користувач не існує.
        """
        try:
            User.objects.get(email=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("User with this email does not exist.")
        return value

    def validate(self, attrs):
        """Перевірити, чи користувач вже не є членом.

        Args:
            attrs (dict): Атрибути.

        Returns:
            dict: Валідовані атрибути.

        Raises:
            serializers.ValidationError: Якщо користувач вже член.
        """
        # Отримати організацію з context
        organization = self.context.get("organization")
        user = User.objects.get(email=attrs["user_email"])

        if organization:
            if OrganizationMembership.objects.filter(
                user=user, organization=organization
            ).exists():
                raise serializers.ValidationError(
                    "This user is already a member of this organization."
                )

        return attrs
