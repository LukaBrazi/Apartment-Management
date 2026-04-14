import pytest
from rest_framework.test import APIRequestFactory
from rest_framework.views import APIView
from django.contrib.auth import get_user_model
from apps.organizations.models import Organization, OrganizationMembership, OrgRole, OrganizationType
from apps.organizations.permissions import IsSuperAdmin, IsDirectorOrAbove, IsAdminOrAbove

User = get_user_model()


@pytest.mark.django_db
class TestIsSuperAdmin:
    """Tests for IsSuperAdmin permission class"""

    def test_superuser_allowed(self, superadmin):
        """Test that superuser is allowed access"""
        rf = APIRequestFactory()
        request = rf.get("/")
        request.user = superadmin

        permission = IsSuperAdmin()
        assert permission.has_permission(request, APIView()) is True

    def test_regular_user_denied(self, director_user):
        """Test that regular user is denied access"""
        rf = APIRequestFactory()
        request = rf.get("/")
        request.user = director_user

        permission = IsSuperAdmin()
        assert permission.has_permission(request, APIView()) is False

    def test_admin_user_denied(self, org_with_members, admin_user):
        """Test that admin user (but not superuser) is denied access"""
        rf = APIRequestFactory()
        request = rf.get("/")
        request.user = admin_user

        permission = IsSuperAdmin()
        assert permission.has_permission(request, APIView()) is False

    def test_unauthenticated_user_denied(self):
        """Test that unauthenticated user is denied access"""
        from django.contrib.auth.models import AnonymousUser

        rf = APIRequestFactory()
        request = rf.get("/")
        request.user = AnonymousUser()

        permission = IsSuperAdmin()
        assert permission.has_permission(request, APIView()) is False


@pytest.mark.django_db
class TestIsDirectorOrAbove:
    """Tests for IsDirectorOrAbove permission class"""

    def test_director_allowed(self, org_with_members, director_user):
        """Test that director is allowed access"""
        rf = APIRequestFactory()
        request = rf.get("/")
        request.user = director_user

        # Create mock view
        view = APIView()
        view.kwargs = {"organization_id": org_with_members.id}

        permission = IsDirectorOrAbove()
        assert permission.has_permission(request, view) is True

    def test_admin_denied(self, org_with_members, admin_user):
        """Test that admin (not director) is denied on specific org operations"""
        rf = APIRequestFactory()
        request = rf.post("/")  # POST request (not GET)
        request.user = admin_user

        view = APIView()
        view.kwargs = {"organization_id": org_with_members.id}

        permission = IsDirectorOrAbove()
        # Admin is not director, so should be denied for POST operations
        result = permission.has_permission(request, view)
        # Admin should not have director-level access
        assert result is False

    def test_staff_denied(self, org_with_members, staff_user):
        """Test that staff is denied access to director-only operations"""
        rf = APIRequestFactory()
        request = rf.post("/")  # POST request for specific org
        request.user = staff_user

        view = APIView()
        view.kwargs = {"organization_id": org_with_members.id}

        permission = IsDirectorOrAbove()
        # Staff should not have director-level access for specific org operations
        assert permission.has_permission(request, view) is False

    def test_resident_denied(self, org_with_members, resident_user):
        """Test that resident is denied access to director-only operations"""
        rf = APIRequestFactory()
        request = rf.post("/")  # POST request for specific org
        request.user = resident_user

        view = APIView()
        view.kwargs = {"organization_id": org_with_members.id}

        permission = IsDirectorOrAbove()
        # Resident should not have director-level access for specific org operations
        assert permission.has_permission(request, view) is False

    def test_non_member_denied(self, org, director_user):
        """Test that non-member is denied access"""
        user = User.objects.create_user(
            email="nonmember@example.com",
            username="nonmember",
            password="testpass123"
        )

        rf = APIRequestFactory()
        request = rf.post("/")  # POST request for specific org
        request.user = user

        view = APIView()
        view.kwargs = {"organization_id": org.id}

        permission = IsDirectorOrAbove()
        # Non-member should not have director-level access
        assert permission.has_permission(request, view) is False


@pytest.mark.django_db
class TestIsAdminOrAbove:
    """Tests for IsAdminOrAbove permission class"""

    def test_admin_allowed(self, org_with_members, admin_user):
        """Test that admin is allowed access"""
        rf = APIRequestFactory()
        request = rf.get("/")
        request.user = admin_user

        view = APIView()
        view.kwargs = {"organization_id": org_with_members.id}

        permission = IsAdminOrAbove()
        assert permission.has_permission(request, view) is True

    def test_director_allowed(self, org_with_members, director_user):
        """Test that director is allowed access"""
        rf = APIRequestFactory()
        request = rf.get("/")
        request.user = director_user

        view = APIView()
        view.kwargs = {"organization_id": org_with_members.id}

        permission = IsAdminOrAbove()
        assert permission.has_permission(request, view) is True

    def test_staff_denied(self, org_with_members, staff_user):
        """Test that staff is denied access to admin-level operations"""
        rf = APIRequestFactory()
        request = rf.post("/")  # POST request for specific org
        request.user = staff_user

        view = APIView()
        view.kwargs = {"organization_id": org_with_members.id}

        permission = IsAdminOrAbove()
        # Staff should not have admin-level access for specific org operations
        assert permission.has_permission(request, view) is False

    def test_resident_denied(self, org_with_members, resident_user):
        """Test that resident is denied access to admin-level operations"""
        rf = APIRequestFactory()
        request = rf.post("/")  # POST request for specific org
        request.user = resident_user

        view = APIView()
        view.kwargs = {"organization_id": org_with_members.id}

        permission = IsAdminOrAbove()
        # Resident should not have admin-level access for specific org operations
        assert permission.has_permission(request, view) is False


@pytest.mark.django_db
class TestOrgDataIsolation:
    """Tests for organization data isolation"""

    def test_queryset_filtered_by_org(self, org_with_members, director_user):
        """Test that querysets are filtered by organization"""
        # Create another organization
        other_org = Organization.objects.create(
            name="Other Organization",
            slug="other-org"
        )

        # User should only see their own organizations
        from apps.organizations.roles import OrgPermissionMixin
        user_orgs = OrgPermissionMixin.get_user_organizations(director_user)

        assert org_with_members in user_orgs
        assert other_org not in user_orgs

    def test_cross_org_access_denied(self, db):
        """Test that users cannot access data from other organizations"""
        # Create two organizations
        org1 = Organization.objects.create(name="Org 1", slug="org1")
        org2 = Organization.objects.create(name="Org 2", slug="org2")

        # Create users in different orgs
        user1 = User.objects.create_user(
            email="user1@example.com",
            username="user1",
            password="test"
        )
        user2 = User.objects.create_user(
            email="user2@example.com",
            username="user2",
            password="test"
        )

        OrganizationMembership.objects.create(
            user=user1,
            organization=org1,
            role=OrgRole.DIRECTOR
        )
        OrganizationMembership.objects.create(
            user=user2,
            organization=org2,
            role=OrgRole.DIRECTOR
        )

        # User1 should not be able to see memberships in Org2
        from apps.organizations.roles import OrgPermissionMixin
        user1_orgs = OrgPermissionMixin.get_user_organizations(user1)

        assert org1 in user1_orgs
        assert org2 not in user1_orgs
