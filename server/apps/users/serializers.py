# Imports
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django_countries.serializer_fields import CountryField
from djoser.serializers import UserSerializer
from phonenumber_field.serializerfields import PhoneNumberField
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken

# Get the user model
User = get_user_model()


# Custom User Serializer
class CustomUserSerializer(UserSerializer):
    """CustomUserSerializer

    CustomUserSerializer class is used to serialize a user.

    Extends:
        UserSerializer

    Attributes:
        full_name (ReadOnlyField): The full name of the user.
        gender (ReadOnlyField): The gender of the user's profile.
        slug (ReadOnlyField): The slug of the user's profile.
        occupation (ReadOnlyField): The occupation of the user's profile.
        phone_number (PhoneNumberField): The phone number of the user's profile.
        country (CountryField): The country of origin of the user's profile.
        city (ReadOnlyField): The city of origin of the user's profile.
        avatar (ReadOnlyField): The avatar URL of the user's profile.
        reputation (ReadOnlyField): The reputation of the user's profile.

    Meta Class:
        model (User): The user model.
        fields (tuple): The fields to include in the serialized data.
        read_only_fields (tuple): The fields to make read-only.
    """

    # Attributes
    full_name = serializers.ReadOnlyField()
    gender = serializers.ReadOnlyField(source="profile.gender")
    slug = serializers.ReadOnlyField(source="profile.slug")
    occupation = serializers.ReadOnlyField(source="profile.occupation")
    phone_number = PhoneNumberField(source="profile.phone_number")
    country = CountryField(source="profile.country_of_origin")
    city = serializers.ReadOnlyField(source="profile.city_of_origin")
    avatar = serializers.ReadOnlyField(source="profile.avatar.url")
    reputation = serializers.ReadOnlyField(source="profile.reputation")

    # Meta Class
    class Meta(UserSerializer.Meta):
        """Meta Class

        Attributes:
            model (User): The user model.
            fields (tuple): The fields to include in the serialized data.
            read_only_fields (tuple): The fields to make read-only.
        """

        # Attributes
        model = User
        fields = (
            "id",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "username",
            "slug",
            "gender",
            "occupation",
            "phone_number",
            "country",
            "city",
            "avatar",
            "reputation",
            "date_joined",
        )
        read_only_fields = ("id", "email", "date_joined")


# ── Remember-Me Aware Token Obtain Pair Serializer ───────────────────────────
class RememberAwareTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Login serializer with optional `remember_me` support.

    Extends SimpleJWT's TokenObtainPairSerializer:

      - Accepts an extra `remember_me: bool` input field (write-only,
        defaults to False so existing clients are unaffected).
      - When `remember_me=True`, mutates the already-signed refresh token
        in-memory to (a) add a `remember: true` custom claim and (b)
        extend its `exp` to settings.REMEMBER_ME_REFRESH_LIFETIME. The
        matching access token is re-derived from the updated refresh.
      - When `remember_me=False` (or absent), returns stock tokens —
        zero behavioral change versus the pre-feature code path.

    The `remember` claim is the single source of truth for session
    persistence. Embedding it in the JWT itself means:

      1. It survives refresh-token rotation (the refresh view reads the
         claim and re-applies the same cookie Max-Age) without needing a
         parallel server-side marker that could desync.
      2. It can't be forged by the client without invalidating the
         signature.
      3. A forgotten-checkbox bug can't silently degrade a remembered
         session into a 5-minute one.

    We deliberately mutate the existing refresh token rather than calling
    RefreshToken.for_user() afresh — the latter would create a second
    OutstandingToken row per login. Our mutation keeps the same JTI, so
    blacklist tracking stays consistent; if OutstandingToken.expires_at
    ends up stale, the blacklist path self-heals via get_or_create.
    """

    remember_me = serializers.BooleanField(
        required=False, default=False, write_only=True
    )

    def validate(self, attrs):
        # Pop before super() — SimpleJWT's parent validate() wouldn't
        # know what to do with an unknown field.
        remember = bool(attrs.pop("remember_me", False))
        data = super().validate(attrs)

        if remember:
            rt = RefreshToken(data["refresh"])
            rt["remember"] = True
            rt.set_exp(
                lifetime=getattr(
                    settings,
                    "REMEMBER_ME_REFRESH_LIFETIME",
                    timedelta(days=14),
                )
            )
            data["refresh"] = str(rt)
            data["access"] = str(rt.access_token)

        return data
