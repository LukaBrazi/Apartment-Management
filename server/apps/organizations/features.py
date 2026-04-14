# Imports
from enum import Enum

from django.utils.translation import gettext_lazy as _


# ── Feature Enum ───────────────────────────────────────────────────────────────

class Feature(str, Enum):
    """Feature

    Функції, які можна активувати в організації.

    Attributes:
        PASSES (str): Проходи/пропуски.
        ISSUES (str): Заявки на усунення неполадок.
        NEWS (str): Новини.
        PAYMENTS (str): Платежі.
        RATINGS (str): Рейтинги.
        REPORTS (str): Звіти.
    """

    PASSES = "passes"
    ISSUES = "issues"
    NEWS = "news"
    PAYMENTS = "payments"
    RATINGS = "ratings"
    REPORTS = "reports"


# ── Default Features ──────────────────────────────────────────────────────────

DEFAULT_FEATURES = {
    Feature.ISSUES: True,
    Feature.NEWS: True,
    Feature.PASSES: False,
    Feature.PAYMENTS: False,
    Feature.RATINGS: False,
    Feature.REPORTS: False,
}


# ── Feature Flag Service ───────────────────────────────────────────────────────

class FeatureService:
    """FeatureService

    Сервіс для управління функціями організації.

    Methods:
        is_enabled: Перевірити, активна ли функція.
        enable: Активувати функцію.
        disable: Деактивувати функцію.
    """

    @staticmethod
    def is_enabled(org, feature: str) -> bool:
        """Перевірити, активна ли функція в організації.

        Args:
            org (Organization): Організація.
            feature (str): Назва функції.

        Returns:
            bool: True якщо функція активна, False інакше.
        """
        return org.is_feature_enabled(feature)

    @staticmethod
    def enable(org, feature: str) -> None:
        """Активувати функцію в організації.

        Args:
            org (Organization): Організація.
            feature (str): Назва функції.
        """
        org.features[feature] = True
        org.save(update_fields=["features"])

    @staticmethod
    def disable(org, feature: str) -> None:
        """Деактивувати функцію в організації.

        Args:
            org (Organization): Організація.
            feature (str): Назва функції.
        """
        org.features[feature] = False
        org.save(update_fields=["features"])


# ── Feature Required Mixin ─────────────────────────────────────────────────────

class FeatureRequiredMixin:
    """FeatureRequiredMixin

    Допоміжний клас для перевірки активації функції.

    Attributes:
        required_feature (str): Назва функції, що вимагається.

    Methods:
        check_permissions: Перевірити, чи активна функція.
    """

    required_feature: str = None

    def check_permissions(self, request):
        """Перевірити дозволи та наявність функції.

        Args:
            request: HTTP request.

        Raises:
            PermissionDenied: Якщо функція не активна.
        """
        # Спочатку перевірити стандартні дозволи
        super().check_permissions(request)

        # Якщо требуется перевірка функції
        if self.required_feature:
            org = self._get_organization(request)
            if org and not FeatureService.is_enabled(org, self.required_feature):
                from rest_framework.exceptions import PermissionDenied

                raise PermissionDenied(
                    f"Feature '{self.required_feature}' is not enabled for this organization."
                )

    def _get_organization(self, request):
        """Отримати організацію з request.

        Args:
            request: HTTP request.

        Returns:
            Organization | None: Організація або None.
        """
        if hasattr(self, "kwargs") and "organization_id" in self.kwargs:
            from apps.organizations.models import Organization

            try:
                return Organization.objects.get(id=self.kwargs["organization_id"])
            except Organization.DoesNotExist:
                return None
        return None
