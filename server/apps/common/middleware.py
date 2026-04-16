"""
Organization detection middleware for multi-tenant EstateOS.

Detects which Organization the request belongs to via:
1. X-Organization-Slug header (for API clients / mobile)
2. Subdomain: zhk-name.estateos.com → slug="zhk-name"
3. Falls back to None (platform default)

Sets request.organization and request.site_settings.
"""
from django.conf import settings as django_settings


class OrganizationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.organization = self._detect_organization(request)
        # Lazy — don't load SiteSettings on every request
        request._site_settings = None
        return self.get_response(request)

    def _detect_organization(self, request):
        from apps.organizations.models import Organization

        # 1. Explicit header (API clients, mobile app)
        org_slug = request.headers.get("X-Organization-Slug")
        if org_slug:
            return Organization.objects.filter(slug=org_slug, is_active=True).first()

        # 2. Subdomain detection
        host = request.get_host().split(":")[0]  # remove port
        platform_domains = getattr(django_settings, "PLATFORM_DOMAINS", ["localhost", "estateos.com"])
        for domain in platform_domains:
            if host.endswith(f".{domain}"):
                subdomain = host[: -len(domain) - 1]
                return Organization.objects.filter(slug=subdomain, is_active=True).first()

        return None


def get_request_site_settings(request):
    """Helper: get SiteSettings for current request's organization."""
    from apps.site_settings.models import SiteSettings

    if request._site_settings is None:
        request._site_settings = SiteSettings.get_for_org(
            getattr(request, "organization", None)
        )
    return request._site_settings
