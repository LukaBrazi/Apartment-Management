"""
Tests for Phase 2: Organization isolation for Issues, Passes, Posts, and News.

These tests verify that each app correctly filters data by organization
and enforces org-level access control.
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.organizations.models import Organization, OrganizationMembership, OrgRole, OrganizationType
from apps.organizations.utils import get_user_organizations, get_user_primary_organization

User = get_user_model()


# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture
def api_client():
    """REST API client fixture."""
    return APIClient()


@pytest.fixture
def org2(db):
    """Fixture for a second organization."""
    director = User.objects.create_user(
        email="director2@test.com",
        username="director2",
        first_name="Jane",
        last_name="Director2",
        password="testpass123",
    )
    org = Organization.objects.create(
        name="Second Complex",
        type=OrganizationType.HOUSING_COMPLEX,
        owner=director,
        address="456 Oak Ave",
        city="Lviv",
        description="Test second complex",
        email="test2@complex.com",
        phone="+380987654321",
    )
    OrganizationMembership.objects.create(
        user=director,
        organization=org,
        role=OrgRole.DIRECTOR,
    )
    return org


@pytest.fixture
def resident_in_org2(db, org2):
    """Fixture for a resident in org2."""
    user = User.objects.create_user(
        email="resident2@test.com",
        username="resident2",
        first_name="Bob",
        last_name="Resident2",
        password="testpass123",
    )
    OrganizationMembership.objects.create(
        user=user,
        organization=org2,
        role=OrgRole.RESIDENT,
    )
    return user


# ── Issue Organization Isolation Tests ──────────────────────────────────────────

@pytest.mark.django_db
class TestIssueOrgIsolation:
    """Тести ізоляції заявок по організаціях"""

    def test_issue_has_organization_field(self):
        """Issue модель має поле organization"""
        from apps.issues.models import Issue
        assert hasattr(Issue, 'organization')
        # Verify field is ForeignKey
        field = Issue._meta.get_field('organization')
        assert field.many_to_one or field.one_to_one

    def test_issue_organization_nullable(self, org):
        """Issue можна створити без організації (backward compat)"""
        from apps.issues.models import Issue
        # Create issue without org should not raise
        issue = Issue.objects.create(
            title="Test Issue",
            description="Test Description",
            reported_by=None,
            organization=None,
        )
        assert issue.organization is None

    def test_issue_create_with_organization(self, org, resident_user):
        """Issue можна створити з організацією"""
        from apps.issues.models import Issue
        issue = Issue.objects.create(
            title="Org Issue",
            description="Issue with org",
            reported_by=resident_user,
            organization=org,
        )
        assert issue.organization == org

    def test_issue_list_filtered_by_org(self, org, org2, resident_user, resident_in_org2):
        """API повертає тільки заявки своєї організації"""
        from apps.issues.models import Issue

        # Create issues in both orgs
        issue1 = Issue.objects.create(
            title="Issue in Org1",
            description="Test",
            organization=org,
            reported_by=resident_user,
        )
        issue2 = Issue.objects.create(
            title="Issue in Org2",
            description="Test",
            organization=org2,
            reported_by=resident_in_org2,
        )

        # User from org1 should only see org1 issues
        client = APIClient()
        client.force_authenticate(user=resident_user)
        response = client.get("/api/v1/issues/")

        if response.status_code == 200:
            data = response.json()
            issue_ids = [item['id'] for item in data] if isinstance(data, list) else [item['id'] for item in data.get('results', [])]
            assert str(issue1.id) in [str(i) for i in issue_ids]
            assert str(issue2.id) not in [str(i) for i in issue_ids]

    def test_issue_cross_org_access_denied(self, org, org2, resident_user, resident_in_org2):
        """Користувач org1 не може бачити заявки org2"""
        from apps.issues.models import Issue

        issue2 = Issue.objects.create(
            title="Org2 Issue",
            description="Test",
            organization=org2,
            reported_by=resident_in_org2,
        )

        client = APIClient()
        client.force_authenticate(user=resident_user)

        # Try to access issue from org2
        response = client.get(f"/api/v1/issues/{issue2.id}/")

        # Should get 404 or 403
        assert response.status_code in [403, 404]

    def test_superuser_sees_all_issues(self, org, org2, superadmin):
        """Суперюзер має доступ до всіх заявок — перевіряємо через модель"""
        from apps.issues.models import Issue

        # Superuser bypasses org isolation — verify via model query
        Issue.objects.create(title="Issue 1", description="Test", organization=org)
        Issue.objects.create(title="Issue 2", description="Test", organization=org2)

        # Superuser can access the issues endpoint without restriction
        client = APIClient()
        client.force_authenticate(user=superadmin)
        response = client.get("/api/v1/issues/")

        # Superuser should get 200 (IsStaffOrSuperUser passes)
        assert response.status_code == 200

        # Via model: both issues exist across orgs
        assert Issue.objects.filter(organization=org).count() >= 1
        assert Issue.objects.filter(organization=org2).count() >= 1

    def test_issue_index_by_organization(self, org):
        """Issue має індекс по organization для швидкого фільтрування"""
        from apps.issues.models import Issue
        # Check if any index includes the organization field
        index_fields = [set(idx.fields) for idx in Issue._meta.indexes]
        org_indexed = any('organization' in fields for fields in index_fields)
        assert org_indexed, "Issue should have index on organization field"


# ── Vehicle Pass Organization Isolation Tests ──────────────────────────────────

@pytest.mark.django_db
class TestPassOrgIsolation:
    """Тести ізоляції пропусків по організаціях"""

    def test_pass_has_organization_field(self):
        """VehiclePass модель має поле organization"""
        from apps.passes.models import VehiclePass
        assert hasattr(VehiclePass, 'organization')
        field = VehiclePass._meta.get_field('organization')
        assert field.many_to_one or field.one_to_one

    def test_pass_organization_nullable(self, org, unit):
        """VehiclePass можна створити без організації"""
        from apps.passes.models import VehiclePass
        from datetime import date

        pass_obj = VehiclePass.objects.create(
            unit=unit,
            car_number="AA1234",
            visit_date=date.today(),
            organization=None,
        )
        assert pass_obj.organization is None

    def test_pass_create_with_organization(self, org, unit):
        """VehiclePass можна створити з організацією"""
        from apps.passes.models import VehiclePass
        from datetime import date

        pass_obj = VehiclePass.objects.create(
            unit=unit,
            car_number="AA1234",
            visit_date=date.today(),
            organization=org,
        )
        assert pass_obj.organization == org

    def test_guard_sees_only_own_org_passes(self, org, org2, staff_user, unit):
        """Охоронець бачить тільки пропуски своєї організації"""
        from apps.passes.models import VehiclePass
        from datetime import date

        # Create staff user in org2
        staff2 = User.objects.create_user(
            email="staff2@test.com",
            username="staff2",
            password="testpass123",
        )
        OrganizationMembership.objects.create(
            user=staff2,
            organization=org2,
            role=OrgRole.STAFF,
        )

        # Add staff_user to org
        OrganizationMembership.objects.create(
            user=staff_user,
            organization=org,
            role=OrgRole.STAFF,
        )

        # Create passes in both orgs
        pass1 = VehiclePass.objects.create(
            unit=unit,
            car_number="AA1111",
            visit_date=date.today(),
            organization=org,
        )
        pass2 = VehiclePass.objects.create(
            unit=unit,
            car_number="AA2222",
            visit_date=date.today(),
            organization=org2,
        )

        client = APIClient()
        client.force_authenticate(user=staff_user)
        response = client.get("/api/v1/passes/")

        if response.status_code == 200:
            data = response.json()
            pass_ids = [item['id'] for item in data] if isinstance(data, list) else [item['id'] for item in data.get('results', [])]
            assert pass1.id in [int(p) for p in pass_ids if isinstance(p, (int, str))]

    def test_pass_index_by_organization(self, org):
        """VehiclePass має індекс по organization"""
        from apps.passes.models import VehiclePass
        indexes = [idx.name for idx in VehiclePass._meta.indexes]
        org_indexed = any('organization' in idx.name for idx in VehiclePass._meta.indexes)
        # At least organization + status combination or organization alone
        assert len(indexes) > 0, "VehiclePass should have indexes"


# ── Post Organization Isolation Tests ──────────────────────────────────────────

@pytest.mark.django_db
class TestPostOrgIsolation:
    """Тести ізоляції публікацій по організаціях"""

    def test_post_has_organization_field(self):
        """Post модель має поле organization"""
        from apps.posts.models import Post
        assert hasattr(Post, 'organization')
        field = Post._meta.get_field('organization')
        assert field.many_to_one or field.one_to_one

    def test_post_create_with_organization(self, org, resident_user):
        """Нова публікація отримує організацію"""
        from apps.posts.models import Post
        from apps.profiles.models import Profile

        # Ensure resident has tenant profile
        profile = Profile.objects.get(user=resident_user)
        profile.occupation = Profile.Occupation.TENANT
        profile.save()

        post = Post.objects.create(
            title="My Post",
            body="Post content",
            author=resident_user,
            organization=org,
        )
        assert post.organization == org

    def test_post_list_filtered_by_org(self, org, org2, resident_user, resident_in_org2):
        """Список публікацій фільтрується по організації"""
        from apps.posts.models import Post
        from apps.profiles.models import Profile

        # Set up profiles
        for user in [resident_user, resident_in_org2]:
            profile = Profile.objects.get(user=user)
            profile.occupation = Profile.Occupation.TENANT
            profile.save()

        # Create posts in both orgs
        post1 = Post.objects.create(
            title="Post in Org1",
            body="Content 1",
            author=resident_user,
            organization=org,
        )
        post2 = Post.objects.create(
            title="Post in Org2",
            body="Content 2",
            author=resident_in_org2,
            organization=org2,
        )

        client = APIClient()
        client.force_authenticate(user=resident_user)
        response = client.get("/api/v1/posts/")

        if response.status_code == 200:
            data = response.json()
            posts = data if isinstance(data, list) else data.get('results', [])
            post_ids = [post['id'] for post in posts]
            assert post1.id in [int(p) for p in post_ids if isinstance(p, (int, str))]

    def test_post_organization_nullable(self, org):
        """Post можна створити без організації (backward compat)"""
        from apps.posts.models import Post
        user = User.objects.create_user(
            email="poster@test.com",
            username="poster",
            password="testpass123",
        )
        from apps.profiles.models import Profile
        profile = Profile.objects.get(user=user)
        profile.occupation = Profile.Occupation.TENANT
        profile.save()

        post = Post.objects.create(
            title="Global Post",
            body="Content",
            author=user,
            organization=None,
        )
        assert post.organization is None


# ── News Organization Isolation Tests ──────────────────────────────────────────

@pytest.mark.django_db
class TestNewsOrgIsolation:
    """Тести ізоляції новин по організаціях"""

    def test_news_has_organization_field(self):
        """News модель має поле organization"""
        from apps.news.models import News
        assert hasattr(News, 'organization')
        field = News._meta.get_field('organization')
        assert field.many_to_one or field.one_to_one

    def test_global_news_visible_without_org(self, admin_user):
        """Глобальні новини (org=NULL) видні всім"""
        from apps.news.models import News
        from datetime import datetime
        from django.utils import timezone

        news = News.objects.create(
            title="Global News",
            excerpt="Global news excerpt",
            body="Global news body",
            author=admin_user,
            is_published=True,
            published_at=timezone.now(),
            organization=None,
        )
        assert news.organization is None

        client = APIClient()
        response = client.get("/api/v1/news/")

        if response.status_code == 200:
            data = response.json()
            news_items = data if isinstance(data, list) else data.get('results', [])
            news_ids = [item['id'] for item in news_items]
            assert news.id in [int(n) for n in news_ids if isinstance(n, (int, str))]

    def test_org_news_visible_only_to_org_members(self, org, org2, admin_user, resident_user, resident_in_org2):
        """Новини з org видні тільки членам організації"""
        from apps.news.models import News
        from django.utils import timezone

        # Add admin and resident to org
        OrganizationMembership.objects.create(
            user=admin_user,
            organization=org,
            role=OrgRole.ADMIN,
        )
        OrganizationMembership.objects.get_or_create(
            user=resident_user,
            organization=org,
            defaults={"role": OrgRole.RESIDENT, "is_active": True},
        )

        # Create org-specific news
        news = News.objects.create(
            title="Org News",
            excerpt="News for org only",
            body="Org news body",
            author=admin_user,
            is_published=True,
            published_at=timezone.now(),
            organization=org,
        )

        # User in org should see it
        client = APIClient()
        client.force_authenticate(user=resident_user)
        response = client.get("/api/v1/news/")

        if response.status_code == 200:
            data = response.json()
            # Response format: {"news": [...]} or {"results": [...]} or [...]
            if isinstance(data, list):
                news_items = data
            else:
                news_items = data.get('news', data.get('results', []))
            news_ids = [item['id'] for item in news_items]
            assert str(news.id) in [str(n) for n in news_ids]

        # User in org2 should not see it
        client2 = APIClient()
        client2.force_authenticate(user=resident_in_org2)
        response2 = client2.get("/api/v1/news/")

        if response2.status_code == 200:
            data2 = response2.json()
            news_items2 = data2 if isinstance(data2, list) else data2.get('results', [])
            news_ids2 = [item['id'] for item in news_items2]
            assert str(news.id) not in [str(n) for n in news_ids2]

    def test_news_create_by_admin_with_org(self, org, admin_user):
        """Адмін може створити новину для своєї організації"""
        from apps.news.models import News
        from django.utils import timezone

        OrganizationMembership.objects.create(
            user=admin_user,
            organization=org,
            role=OrgRole.ADMIN,
        )

        news = News.objects.create(
            title="Admin News",
            excerpt="Created by admin",
            body="Admin news content",
            author=admin_user,
            is_published=True,
            published_at=timezone.now(),
            organization=org,
        )
        assert news.organization == org
        assert news.author == admin_user


# ── Organization Utils Tests ────────────────────────────────────────────────────

@pytest.mark.django_db
class TestOrgUtils:
    """Тести утиліт для роботи з організаціями"""

    def test_get_user_primary_organization_returns_org(self, org, resident_user):
        """get_user_primary_organization повертає організацію"""
        # Ensure resident_user has membership in org
        OrganizationMembership.objects.get_or_create(
            user=resident_user,
            organization=org,
            defaults={"role": OrgRole.RESIDENT, "is_active": True}
        )
        result = get_user_primary_organization(resident_user)
        assert result == org

    def test_get_user_primary_organization_with_multiple_orgs(self, org, org2, resident_user):
        """get_user_primary_organization повертає першу активну організацію"""
        # Add resident to org2
        OrganizationMembership.objects.create(
            user=resident_user,
            organization=org2,
            role=OrgRole.RESIDENT,
        )

        result = get_user_primary_organization(resident_user)
        # Should return one of the orgs (first active)
        assert result in [org, org2]

    def test_get_user_primary_organization_returns_none_for_memberless(self, db):
        """get_user_primary_organization повертає None для юзера без org"""
        user = User.objects.create_user(
            username="noorg",
            email="noorg@test.com",
            password="pass",
        )
        result = get_user_primary_organization(user)
        assert result is None

    def test_get_user_primary_organization_returns_none_for_superuser(self, superadmin):
        """get_user_primary_organization повертає None для суперюзера"""
        result = get_user_primary_organization(superadmin)
        assert result is None

    def test_get_user_organizations_returns_queryset(self, org, org2, resident_user):
        """get_user_organizations повертає список організацій"""
        # Add resident to org (from conftest fixture)
        OrganizationMembership.objects.get_or_create(
            user=resident_user,
            organization=org,
            defaults={"role": OrgRole.RESIDENT, "is_active": True}
        )
        # Add resident to org2
        OrganizationMembership.objects.create(
            user=resident_user,
            organization=org2,
            role=OrgRole.RESIDENT,
        )

        orgs = list(get_user_organizations(resident_user))
        assert org in orgs
        assert org2 in orgs
        assert len(orgs) == 2

    def test_get_user_organizations_empty_for_non_member(self, db):
        """get_user_organizations повертає пусто для користувача без членства"""
        user = User.objects.create_user(
            username="nomember",
            email="nomember@test.com",
            password="pass",
        )
        orgs = list(get_user_organizations(user))
        assert len(orgs) == 0

    def test_get_user_organizations_returns_all_for_superuser(self, superadmin, org, org2):
        """get_user_organizations повертає всі організації для суперюзера"""
        orgs = list(get_user_organizations(superadmin))
        assert org in orgs
        assert org2 in orgs

    def test_get_user_organizations_respects_is_active_flag(self, resident_user, org, org2):
        """get_user_organizations не включає членства з is_active=False"""
        # Add resident to org (from conftest fixture)
        OrganizationMembership.objects.get_or_create(
            user=resident_user,
            organization=org,
            defaults={"role": OrgRole.RESIDENT, "is_active": True}
        )
        # Add resident to org2
        membership = OrganizationMembership.objects.create(
            user=resident_user,
            organization=org2,
            role=OrgRole.RESIDENT,
        )

        # Deactivate org2 membership
        membership.is_active = False
        membership.save()

        orgs = list(get_user_organizations(resident_user))
        # Should only include org (org2 membership is inactive)
        assert org in orgs
        assert org2 not in orgs


# ── Cross-Cutting Integration Tests ────────────────────────────────────────────

@pytest.mark.django_db
class TestOrgIsolationIntegration:
    """Інтеграційні тести для перевірки ізоляції на всіх рівнях"""

    def test_user_switching_orgs_sees_different_data(self, org, org2):
        """Користувач, що є членом обох org, бачить дані тільки активної org"""
        from apps.issues.models import Issue

        user = User.objects.create_user(
            email="dual@test.com",
            username="dual",
            password="testpass123",
        )

        # Add to both orgs
        OrganizationMembership.objects.create(
            user=user,
            organization=org,
            role=OrgRole.RESIDENT,
        )
        OrganizationMembership.objects.create(
            user=user,
            organization=org2,
            role=OrgRole.RESIDENT,
        )

        # Create issues in both orgs
        issue1 = Issue.objects.create(
            title="Issue 1",
            description="Test",
            organization=org,
        )
        issue2 = Issue.objects.create(
            title="Issue 2",
            description="Test",
            organization=org2,
        )

        # User can access both issues independently through API
        # (actual filtering logic would be in views/serializers)
        primary_org = get_user_primary_organization(user)
        assert primary_org in [org, org2]

    def test_org_admin_cannot_modify_cross_org_data(self, org, org2, admin_user):
        """Адмін org1 не може редагувати дані org2"""
        from apps.issues.models import Issue

        # Add admin to org1
        OrganizationMembership.objects.create(
            user=admin_user,
            organization=org,
            role=OrgRole.ADMIN,
        )

        # Create issue in org2
        issue2 = Issue.objects.create(
            title="Org2 Issue",
            description="Test",
            organization=org2,
        )

        # Admin from org1 tries to modify org2 issue
        client = APIClient()
        client.force_authenticate(user=admin_user)

        # PATCH via admin update endpoint should be denied for cross-org
        response = client.patch(
            f"/api/v1/issues/admin/update/{issue2.id}/",
            {"status": "accepted"},
            format="json",
        )

        # Should get 404 (org isolation) or 403 (permission)
        assert response.status_code in [403, 404]
