# Imports
import logging

from django.contrib.auth import get_user_model
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from apps.common.renderers import GenericJSONRenderer
from apps.organizations.features import Feature
from apps.organizations.models import Organization, OrganizationMembership
from apps.organizations.permissions import IsAdminOrAbove, IsDirectorOrAbove
from apps.organizations.serializers import (
    AddMemberSerializer,
    OrganizationCreateSerializer,
    OrganizationDetailSerializer,
    OrganizationMembershipSerializer,
    OrganizationSerializer,
)

User = get_user_model()

# Get the logger
logger = logging.getLogger(__name__)


# ── Organization ViewSet ──────────────────────────────────────────────────────

class OrganizationViewSet(viewsets.ModelViewSet):
    """OrganizationViewSet

    ViewSet для управління організаціями.

    Extends:
        viewsets.ModelViewSet

    Attributes:
        queryset (QuerySet): QuerySet організацій.
        serializer_class (Serializer): Клас серіалізатора.
        renderer_classes (list): Класи рендерерів.
        permission_classes (list): Класи дозволів.

    Methods:
        get_queryset: Отримати QuerySet.
        get_serializer_class: Отримати клас серіалізатора.
        perform_create: Виконати створення організації.
        members: Action для управління членами.
    """

    queryset = Organization.objects.all()
    renderer_classes = (GenericJSONRenderer,)
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        """Отримати QuerySet організацій.

        Суперадміністратори бачать всі організації.
        Звичайні користувачи бачать тільки організації, до яких вони належать.

        Returns:
            QuerySet: QuerySet організацій.
        """
        if self.request.user.is_superuser:
            return Organization.objects.all()

        return Organization.objects.filter(
            memberships__user=self.request.user,
            memberships__is_active=True,
        ).distinct()

    def get_serializer_class(self):
        """Отримати клас серіалізатора.

        Для create - OrganizationCreateSerializer.
        Для retrieve - OrganizationDetailSerializer.
        Для інших - OrganizationSerializer.

        Returns:
            Serializer: Клас серіалізатора.
        """
        if self.action == "create":
            return OrganizationCreateSerializer
        elif self.action == "retrieve":
            return OrganizationDetailSerializer
        return OrganizationSerializer

    def create(self, request, *args, **kwargs):
        """Створити організацію.

        Дозволено тільки авторизованим користувачам.
        Створюється членство DIRECTOR для користувача та встановлюються функції за замовчуванням.

        Args:
            request: HTTP request.

        Returns:
            Response: Відповідь з новою організацією.

        Raises:
            PermissionDenied: Якщо користувач не авторизован.
        """
        if not request.user.is_superuser:
            raise PermissionDenied("Only superusers can create organizations.")

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        org = serializer.save()

        # Створити членство DIRECTOR для власника
        OrganizationMembership.objects.create(
            user=request.user,
            organization=org,
            role="director",
            invited_by=None,
        )

        # Логувати створення
        logger.info(f"Organization '{org.name}' created by {request.user.full_name}")

        # Повернути детальну серіалізацію
        detail_serializer = OrganizationDetailSerializer(org)
        return Response(detail_serializer.data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, *args, **kwargs):
        """Отримати деталі організації.

        Дозволено членам організації та суперадміністраторам.

        Args:
            request: HTTP request.

        Returns:
            Response: Детальна інформація про організацію.

        Raises:
            PermissionDenied: Якщо користувач не має доступу.
        """
        org = self.get_object()

        # Перевірити доступ
        if (
            not request.user.is_superuser
            and not OrganizationMembership.objects.filter(
                user=request.user, organization=org, is_active=True
            ).exists()
        ):
            raise PermissionDenied("You do not have access to this organization.")

        serializer = self.get_serializer(org)
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        """Видалити організацію.

        Дозволено тільки адміністраторам організації та суперадміністраторам.

        Args:
            request: HTTP request.

        Returns:
            Response: Відповідь про видалення.

        Raises:
            PermissionDenied: Якщо користувач не має доступу.
        """
        org = self.get_object()

        # Перевірити доступ
        if not request.user.is_superuser:
            membership = OrganizationMembership.objects.filter(
                user=request.user, organization=org
            ).first()
            if not membership or not membership.is_admin_or_above():
                raise PermissionDenied(
                    "You do not have permission to delete this organization."
                )

        logger.info(f"Organization '{org.name}' deleted by {request.user.full_name}")
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=["get", "post"], url_path="members")
    def members(self, request, pk=None):
        """Управління членами організації.

        GET: Отримати список членів.
        POST: Додати нового члена (потребує ролі ADMIN або вище).

        Args:
            request: HTTP request.
            pk: UUID організації.

        Returns:
            Response: Список членів або результат додавання.

        Raises:
            PermissionDenied: Якщо користувач не має доступу.
        """
        org = self.get_object()

        # Перевірити членство
        membership = OrganizationMembership.objects.filter(
            user=request.user, organization=org
        ).first()
        if not membership and not request.user.is_superuser:
            raise PermissionDenied("You are not a member of this organization.")

        if request.method == "GET":
            # Отримати членів
            members = org.memberships.filter(is_active=True).select_related("user")
            serializer = OrganizationMembershipSerializer(members, many=True)
            return Response(serializer.data)

        elif request.method == "POST":
            # Додати члена
            if not request.user.is_superuser:
                if not membership.is_admin_or_above():
                    raise PermissionDenied(
                        "You do not have permission to add members."
                    )

            serializer = AddMemberSerializer(
                data=request.data,
                context={"organization": org, "request": request},
            )
            serializer.is_valid(raise_exception=True)

            user = User.objects.get(email=serializer.validated_data["user_email"])
            role = serializer.validated_data["role"]
            staff_type = serializer.validated_data.get("staff_type", "")

            # Перевірити, чи користувач вже член
            existing = OrganizationMembership.objects.filter(
                user=user, organization=org
            ).first()
            if existing:
                raise ValidationError(
                    "This user is already a member of this organization."
                )

            # Створити членство
            new_membership = OrganizationMembership.objects.create(
                user=user,
                organization=org,
                role=role,
                staff_type=staff_type,
                invited_by=request.user,
            )

            logger.info(
                f"User {user.full_name} added to {org.name} by {request.user.full_name}"
            )

            serializer = OrganizationMembershipSerializer(new_membership)
            return Response(serializer.data, status=status.HTTP_201_CREATED)


# ── Organization Membership ViewSet ────────────────────────────────────────────

class OrganizationMembershipViewSet(viewsets.ModelViewSet):
    """OrganizationMembershipViewSet

    ViewSet для управління членством в організаціях.

    Extends:
        viewsets.ModelViewSet

    Attributes:
        queryset (QuerySet): QuerySet членства.
        serializer_class (Serializer): Клас серіалізатора.
        renderer_classes (list): Класи рендерерів.
        permission_classes (list): Класи дозволів.

    Methods:
        get_queryset: Отримати QuerySet.
        destroy: Видалити членство.
    """

    queryset = OrganizationMembership.objects.all()
    serializer_class = OrganizationMembershipSerializer
    renderer_classes = (GenericJSONRenderer,)
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        """Отримати QuerySet членства.

        Суперадміністратори бачать все членство.
        Звичайні користувачи бачать членство лише в організаціях, до яких вони належать,
        та тільки якщо вони ADMIN або вище.

        Returns:
            QuerySet: QuerySet членства.
        """
        if self.request.user.is_superuser:
            return OrganizationMembership.objects.all()

        # Отримати організації, де користувач є адміністратором
        admin_orgs = Organization.objects.filter(
            memberships__user=self.request.user,
            memberships__role__in=["super_admin", "director", "admin"],
        )

        return OrganizationMembership.objects.filter(organization__in=admin_orgs)

    def list(self, request, *args, **kwargs):
        """Отримати список членства.

        Args:
            request: HTTP request.

        Returns:
            Response: Список членства.
        """
        # Отримати організацію з query параметрів
        organization_id = request.query_params.get("organization_id")
        if organization_id:
            org = Organization.objects.filter(id=organization_id).first()
            if not org:
                raise PermissionDenied("Organization not found.")

            # Перевірити доступ
            if not request.user.is_superuser:
                membership = OrganizationMembership.objects.filter(
                    user=request.user, organization=org
                ).first()
                if not membership:
                    raise PermissionDenied(
                        "You are not a member of this organization."
                    )

            queryset = org.memberships.filter(is_active=True)
            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data)

        return super().list(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        """Видалити членство.

        Дозволено адміністраторам організації та суперадміністраторам.
        Адміністратор не може видалити самого себе, якщо він останній адміністратор.

        Args:
            request: HTTP request.

        Returns:
            Response: Результат видалення.

        Raises:
            PermissionDenied: Якщо користувач не має доступу.
        """
        membership = self.get_object()
        org = membership.organization

        # Перевірити доступ
        if not request.user.is_superuser:
            actor_membership = OrganizationMembership.objects.filter(
                user=request.user, organization=org
            ).first()
            if not actor_membership or not actor_membership.is_admin_or_above():
                raise PermissionDenied(
                    "You do not have permission to remove members."
                )

        # Перевірити, чи це останній адміністратор
        if membership.is_admin_or_above():
            admin_count = org.memberships.filter(
                role__in=["super_admin", "director", "admin"],
                is_active=True,
            ).count()
            if admin_count <= 1:
                raise ValidationError(
                    "Cannot remove the last administrator from the organization."
                )

        logger.info(
            f"User {membership.user.full_name} removed from {org.name} by {request.user.full_name}"
        )

        membership.is_active = False
        membership.save()

        return Response(status=status.HTTP_204_NO_CONTENT)
