# Imports
from apps.profiles.models import Profile
from django_countries.serializer_fields import CountryField
from rest_framework import serializers


# Profile Serializer
class ProfileSerializer(serializers.ModelSerializer):
    """Profile serializer

    This class is used to serialize a profile.

    Extends:
        serializers.ModelSerializer

    Attributes:
        first_name (ReadOnlyField): The first name of the user.
        last_name (ReadOnlyField): The last name of the user.
        username (ReadOnlyField): The username of the user.
        full_name (ReadOnlyField): The full name of the user.
        country_of_origin (CountryField): The country of origin of the user.
        avatar (SerializerMethodField): The avatar of the user.
        date_joined (DateTimeField): The date the user joined.
        apartment (SerializerMethodField): The apartment the user belongs to.
        average_rating (SerializerMethodField): The average rating of the user.

    Methods:
        get_avatar(obj: Profile) -> str | None: Get the avatar of the user.
        get_average_rating(obj: Profile) -> float: Get the average rating

    Meta Class:
        model (Profile): The profile model.
        fields (list): The fields to include in the serialized data.
    """

    # Attributes
    first_name = serializers.ReadOnlyField(source="user.first_name")
    last_name = serializers.ReadOnlyField(source="user.last_name")
    username = serializers.ReadOnlyField(source="user.username")
    full_name = serializers.ReadOnlyField(source="user.full_name")
    is_staff = serializers.ReadOnlyField(source="user.is_staff")
    # PR-14: the frontend uses this to gate the ``/admin/telegram-bot``
    # super_admin-only UI.  Exposing ``is_superuser`` is fine — it's a
    # boolean, it's already part of Django's auth contract, and the
    # sensitive tokens remain write-only on the server.
    is_superuser = serializers.ReadOnlyField(source="user.is_superuser")
    country_of_origin = CountryField(name_only=True)
    avatar = serializers.SerializerMethodField()
    date_joined = serializers.DateTimeField(source="user.date_joined", read_only=True)
    average_rating = serializers.SerializerMethodField()
    # Unit / building fields resolve via ``Profile.primary_unit`` (the
    # tenant's primary ``Residency``) — canonical after PR-11.
    unit_number = serializers.SerializerMethodField()
    unit_id = serializers.SerializerMethodField()
    building_name = serializers.SerializerMethodField()
    building_id = serializers.SerializerMethodField()
    managed_buildings = serializers.SerializerMethodField()

    # Meta Class
    class Meta:
        """Meta Class

        Attributes:
            model (Profile): The profile model.
            fields (list): The fields to include in the serialized data.
        """

        # Attributes
        model = Profile
        fields = [
            "id",
            "slug",
            "first_name",
            "last_name",
            "username",
            "full_name",
            "gender",
            "country_of_origin",
            "city_of_origin",
            "bio",
            "is_staff",
            "is_superuser",
            "occupation",
            "reputation",
            "date_joined",
            "avatar",
            "unit_id",
            "unit_number",
            "building_name",
            "building_id",
            "managed_buildings",
            "average_rating",
        ]
        read_only_fields = ["occupation", "reputation", "report_count", "slug"]

    # Method to get the avatar url
    def get_avatar(self, obj: Profile) -> str | None:
        """Get the avatar of the user.

        Args:
            obj (Profile): The profile.

        Returns:
            str | None: The avatar of the user.
        """

        # Try to get the avatar url
        try:
            return obj.avatar.url

        # If the avatar does not exist
        except ValueError:
            # Return None
            return None

    # PR-10 accessor helpers — resolve the tenant's unit via
    # ``primary_unit`` so multi-unit residents see their primary home
    # consistently across the Profile payload.
    def get_unit_number(self, obj: Profile):
        unit = obj.primary_unit
        return unit.number if unit is not None else None

    def get_unit_id(self, obj: Profile):
        unit = obj.primary_unit
        return str(unit.id) if unit is not None else None

    def get_building_name(self, obj: Profile):
        unit = obj.primary_unit
        if unit is not None and unit.entrance_id:
            return unit.entrance.building.name
        return None

    def get_building_id(self, obj: Profile):
        unit = obj.primary_unit
        if unit is not None and unit.entrance_id:
            return str(unit.entrance.building.id)
        return None

    def get_managed_buildings(self, obj: Profile) -> list:
        return list(obj.buildings.values("id", "name", "address"))

    # Method to get the average rating
    def get_average_rating(self, obj: Profile) -> float:
        """Get the average rating.

        Args:
            obj (Profile): The profile.

        Returns:
            float: The average rating.
        """

        # Return the average rating
        return obj.get_average_rating()


# Update Profile Serializer
class UpdateProfileSerializer(serializers.ModelSerializer):
    """Update profile serializer

    This class is used to serialize the update of a profile.

    Extends:
        serializers.ModelSerializer

    Attributes:
        first_name (ReadOnlyField): The first name of the user.
        last_name (ReadOnlyField): The last name of the user.
        username (ReadOnlyField): The username of the user.
        country_of_origin (CountryField): The country of origin of the user.

    Meta Class:
        model (Profile): The profile model.
        fields (list): The fields to include in the serialized data.
    """

    # Attributes
    first_name = serializers.ReadOnlyField(source="user.first_name")
    last_name = serializers.ReadOnlyField(source="user.last_name")
    username = serializers.ReadOnlyField(source="user.username")
    country_of_origin = CountryField(name_only=True)

    # Meta Class
    class Meta:
        """Meta Class

        Attributes:
            model (Profile): The profile model.
            fields (list): The fields to include in the serialized data.
        """

        # Attributes
        model = Profile
        fields = [
            "first_name",
            "last_name",
            "username",
            "gender",
            "country_of_origin",
            "city_of_origin",
            "bio",
            "occupation",
            "phone_number",
        ]
        read_only_fields = ["occupation"]


class AdminUpdateProfileSerializer(serializers.ModelSerializer):
    """Serializer for admin profile updates — allows changing occupation and unit."""

    country_of_origin = CountryField(name_only=True)
    occupation = serializers.ChoiceField(choices=Profile.Occupation.choices, required=False)
    unit_id = serializers.UUIDField(required=False, allow_null=True, write_only=True)

    class Meta:
        model = Profile
        fields = [
            "gender",
            "country_of_origin",
            "city_of_origin",
            "bio",
            "occupation",
            "phone_number",
            "unit_id",
        ]

    def update(self, instance, validated_data):
        unit_id = validated_data.pop("unit_id", ...)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # PR-11: ``Profile.unit`` FK removed — writes go through the
        # ``Residency`` through-model.  ``unit_id=None`` clears any
        # primary residency; a concrete id promotes that Unit to the
        # user's primary residency (and demotes any prior primary).
        if unit_id is not ...:
            from apps.apartments.models import Residency, ResidencyRole, Unit

            user = instance.user
            if unit_id is None:
                Residency.objects.filter(user=user, is_primary=True).update(
                    is_primary=False
                )
            else:
                unit = Unit.objects.get(id=unit_id)
                Residency.objects.update_or_create(
                    user=user,
                    unit=unit,
                    defaults={
                        "role": ResidencyRole.OWNER,
                        "is_primary": True,
                    },
                )
                Residency.objects.filter(user=user, is_primary=True).exclude(
                    unit=unit
                ).update(is_primary=False)
        return instance


class AdminCreateUserSerializer(serializers.Serializer):
    email = serializers.EmailField()
    username = serializers.CharField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    password = serializers.CharField(write_only=True)
    occupation = serializers.ChoiceField(choices=Profile.Occupation.choices)
    unit_id = serializers.UUIDField(required=False, allow_null=True)

    def validate_email(self, value):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("User with this email already exists.")
        return value

    def validate_username(self, value):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("User with this username already exists.")
        return value

    def create(self, validated_data):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        occupation = validated_data.pop("occupation")
        password = validated_data.pop("password")
        unit_id = validated_data.pop("unit_id", None)
        user = User.objects.create(**validated_data, is_active=True)
        user.set_password(password)
        user.save()
        Profile.objects.filter(user=user).update(occupation=occupation)

        # PR-11: assign the Unit via the ``Residency`` through-model —
        # ``Profile.unit`` FK no longer exists.
        if unit_id:
            from apps.apartments.models import Residency, ResidencyRole, Unit

            unit = Unit.objects.get(id=unit_id)
            Residency.objects.update_or_create(
                user=user,
                unit=unit,
                defaults={
                    "role": ResidencyRole.OWNER,
                    "is_primary": True,
                },
            )
            Residency.objects.filter(user=user, is_primary=True).exclude(
                unit=unit
            ).update(is_primary=False)
        return user


# Avatar Upload Serializer
class AvatarUploadSerializer(serializers.ModelSerializer):
    """Avatar upload serializer

    This class is used to serialize the upload of an avatar.

    Extends:
        serializers.ModelSerializer

    Meta Class:
        model (Profile): The profile model.
        fields (list): The fields to include in the serialized data.
    """

    # Meta Class
    class Meta:
        """Meta Class

        Attributes:
            model (Profile): The profile model.
            fields (list): The fields to include in the serialized data.
        """

        # Attributes
        model = Profile
        fields = ["avatar"]

    def validate_avatar(self, value):
        """Validate avatar file: type and size constraints."""
        allowed_types = ["image/jpeg", "image/png", "image/webp", "image/gif"]
        max_size_mb = 5

        # Check content type
        if hasattr(value, "content_type") and value.content_type not in allowed_types:
            raise serializers.ValidationError(
                f"Unsupported file type: {value.content_type}. "
                "Allowed types: JPEG, PNG, WebP, GIF."
            )

        # Check extension as fallback
        import os
        ext = os.path.splitext(value.name)[1].lower()
        allowed_exts = [".jpg", ".jpeg", ".png", ".webp", ".gif"]
        if ext not in allowed_exts:
            raise serializers.ValidationError(
                f"Invalid file extension '{ext}'. Allowed: .jpg, .jpeg, .png, .webp, .gif"
            )

        # Check file size
        if value.size > max_size_mb * 1024 * 1024:
            raise serializers.ValidationError(
                f"File too large. Maximum size is {max_size_mb} MB."
            )

        return value
