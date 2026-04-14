import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from apps.organizations.models import Organization, OrganizationMembership, OrgRole, OrganizationType
from apps.apartments.models import Building, Entrance, Unit

User = get_user_model()


@pytest.mark.django_db
class TestOrganizationModel:
    """Tests for Organization model"""

    def test_organization_creation(self, org):
        """Test that organization can be created with required fields"""
        assert org.name == "Test Complex"
        assert org.slug is not None
        assert org.type == OrganizationType.HOUSING_COMPLEX
        assert org.is_active is True

    def test_organization_str(self, org):
        """Test string representation of organization"""
        assert str(org) == "Test Complex"

    def test_slug_auto_generated(self, db, director_user):
        """Test that slug is auto-generated from name if not provided"""
        org = Organization.objects.create(
            name="My New Organization",
            type=OrganizationType.COTTAGE_VILLAGE
        )
        assert org.slug == "my-new-organization"

    def test_is_feature_enabled_true(self, org):
        """Test feature flag check when enabled"""
        org.features = {"issues": True, "news": False}
        org.save()
        assert org.is_feature_enabled("issues") is True

    def test_is_feature_enabled_false(self, org):
        """Test feature flag check when disabled"""
        org.features = {"issues": True, "news": False}
        org.save()
        assert org.is_feature_enabled("news") is False

    def test_is_feature_enabled_nonexistent(self, org):
        """Test feature flag check for non-existent feature"""
        org.features = {"issues": True}
        org.save()
        assert org.is_feature_enabled("nonexistent") is False

    def test_get_enabled_features(self, org):
        """Test getting list of enabled features"""
        org.features = {"issues": True, "news": True, "passes": False}
        org.save()
        enabled = org.get_enabled_features()
        assert "issues" in enabled
        assert "news" in enabled
        assert "passes" not in enabled
        assert len(enabled) == 2

    def test_organization_types_exist(self):
        """Test that all organization types are defined"""
        assert OrganizationType.HOUSING_COMPLEX == "housing_complex"
        assert OrganizationType.COTTAGE_VILLAGE == "cottage_village"
        assert OrganizationType.MANAGEMENT_COMPANY == "management_company"

    def test_default_is_active_true(self, db):
        """Test that is_active defaults to True"""
        org = Organization.objects.create(
            name="Active Org",
            slug="active-org"
        )
        assert org.is_active is True

    def test_organization_has_uuid(self, org):
        """Test that organization has UUID id"""
        assert org.id is not None
        assert len(str(org.id)) == 36  # UUID length


@pytest.mark.django_db
class TestOrganizationMembershipModel:
    """Tests for OrganizationMembership model"""

    def test_membership_creation(self, org, resident_user):
        """Test that membership can be created"""
        membership = OrganizationMembership.objects.create(
            user=resident_user,
            organization=org,
            role=OrgRole.RESIDENT
        )
        assert membership.user == resident_user
        assert membership.organization == org
        assert membership.role == OrgRole.RESIDENT

    def test_membership_str(self, org, resident_user):
        """Test string representation of membership"""
        membership = OrganizationMembership.objects.create(
            user=resident_user,
            organization=org,
            role=OrgRole.RESIDENT
        )
        assert "Test Complex" in str(membership)
        assert "Resident" in str(membership)

    def test_unique_together_user_org(self, org, resident_user):
        """Test that user-org combination must be unique"""
        OrganizationMembership.objects.create(
            user=resident_user,
            organization=org,
            role=OrgRole.RESIDENT
        )
        with pytest.raises(IntegrityError):
            OrganizationMembership.objects.create(
                user=resident_user,
                organization=org,
                role=OrgRole.ADMIN  # Different role but same user-org
            )

    def test_is_director_or_above_director(self, org, director_user):
        """Test is_director_or_above with director role"""
        # director_user already has director membership in org fixture
        membership = OrganizationMembership.objects.get(
            user=director_user,
            organization=org
        )
        assert membership.is_director_or_above() is True

    def test_is_director_or_above_admin(self, org, admin_user):
        """Test is_director_or_above with admin role"""
        membership = OrganizationMembership.objects.create(
            user=admin_user,
            organization=org,
            role=OrgRole.ADMIN
        )
        assert membership.is_director_or_above() is False

    def test_is_director_or_above_staff(self, org, staff_user):
        """Test is_director_or_above with staff role"""
        membership = OrganizationMembership.objects.create(
            user=staff_user,
            organization=org,
            role=OrgRole.STAFF
        )
        assert membership.is_director_or_above() is False

    def test_is_director_or_above_resident(self, org, resident_user):
        """Test is_director_or_above with resident role"""
        membership = OrganizationMembership.objects.create(
            user=resident_user,
            organization=org,
            role=OrgRole.RESIDENT
        )
        assert membership.is_director_or_above() is False

    def test_is_admin_or_above_admin(self, org, admin_user):
        """Test is_admin_or_above with admin role"""
        membership = OrganizationMembership.objects.create(
            user=admin_user,
            organization=org,
            role=OrgRole.ADMIN
        )
        assert membership.is_admin_or_above() is True

    def test_is_admin_or_above_director(self, org, director_user):
        """Test is_admin_or_above with director role"""
        # director_user already has director membership in org fixture
        membership = OrganizationMembership.objects.get(
            user=director_user,
            organization=org
        )
        assert membership.is_admin_or_above() is True

    def test_is_admin_or_above_staff(self, org, staff_user):
        """Test is_admin_or_above with staff role"""
        membership = OrganizationMembership.objects.create(
            user=staff_user,
            organization=org,
            role=OrgRole.STAFF
        )
        assert membership.is_admin_or_above() is False

    def test_is_admin_or_above_resident(self, org, resident_user):
        """Test is_admin_or_above with resident role"""
        membership = OrganizationMembership.objects.create(
            user=resident_user,
            organization=org,
            role=OrgRole.RESIDENT
        )
        assert membership.is_admin_or_above() is False

    def test_can_invite_users_admin(self, org, admin_user):
        """Test that admin can invite users"""
        membership = OrganizationMembership.objects.create(
            user=admin_user,
            organization=org,
            role=OrgRole.ADMIN
        )
        assert membership.can_invite_users() is True

    def test_can_invite_users_director(self, org, director_user):
        """Test that director can invite users"""
        # director_user already has director membership in org fixture
        membership = OrganizationMembership.objects.get(
            user=director_user,
            organization=org
        )
        assert membership.can_invite_users() is True

    def test_can_invite_users_resident(self, org, resident_user):
        """Test that resident cannot invite users"""
        membership = OrganizationMembership.objects.create(
            user=resident_user,
            organization=org,
            role=OrgRole.RESIDENT
        )
        assert membership.can_invite_users() is False

    def test_can_invite_users_staff(self, org, staff_user):
        """Test that staff cannot invite users"""
        membership = OrganizationMembership.objects.create(
            user=staff_user,
            organization=org,
            role=OrgRole.STAFF
        )
        assert membership.can_invite_users() is False

    def test_default_role_is_resident(self, director_user):
        """Test that default role is resident"""
        # Create a new org to avoid fixtures
        org = Organization.objects.create(
            name="Test Org",
            slug="test-org"
        )
        user = User.objects.create_user(
            email="newuser@example.com",
            username="newuser",
            password="testpass123"
        )
        membership = OrganizationMembership.objects.create(
            user=user,
            organization=org
        )
        assert membership.role == OrgRole.RESIDENT

    def test_roles_hierarchy(self):
        """Test that all OrgRole values are defined"""
        assert OrgRole.SUPER_ADMIN == "super_admin"
        assert OrgRole.DIRECTOR == "director"
        assert OrgRole.ADMIN == "admin"
        assert OrgRole.STAFF == "staff"
        assert OrgRole.RESIDENT == "resident"

    def test_membership_has_uuid(self, org, resident_user):
        """Test that membership has UUID id"""
        membership = OrganizationMembership.objects.create(
            user=resident_user,
            organization=org,
            role=OrgRole.RESIDENT
        )
        assert membership.id is not None
        assert len(str(membership.id)) == 36


@pytest.mark.django_db
class TestBuildingOrganizationFK:
    """Tests for Building-Organization foreign key relationship"""

    def test_building_has_organization_field(self, org):
        """Test that Building model has organization FK"""
        building = Building.objects.create(
            name="Test Building",
            address="123 Main St",
            organization=org
        )
        assert building.organization == org

    def test_building_organization_nullable(self, db):
        """Test that building organization is nullable"""
        building = Building.objects.create(
            name="Test Building",
            address="123 Main St",
            organization=None
        )
        assert building.organization is None

    def test_building_organization_cascade_delete(self, org):
        """Test that buildings are deleted when organization is deleted"""
        building = Building.objects.create(
            name="Test Building",
            address="123 Main St",
            organization=org
        )
        org_id = org.id
        org.delete()
        assert Building.objects.filter(id=building.id).exists() is False

    def test_entrance_inherits_org_from_building(self, building):
        """Test that entrance inherits organization from building"""
        entrance = Entrance.objects.create(
            building=building,
            name="Entrance 1"
        )
        assert entrance.organization == building.organization

    def test_entrance_org_set_on_save(self, building):
        """Test that entrance organization is set automatically on save"""
        entrance = Entrance(
            building=building,
            name="Entrance 1",
            organization=None
        )
        entrance.save()
        assert entrance.organization == building.organization

    def test_unit_inherits_org_from_entrance(self, entrance):
        """Test that unit inherits organization from entrance"""
        unit = Unit.objects.create(
            entrance=entrance,
            number="101",
            floor=1
        )
        assert unit.organization == entrance.organization

    def test_unit_org_set_on_save(self, entrance):
        """Test that unit organization is set automatically on save"""
        unit = Unit(
            entrance=entrance,
            number="101",
            floor=1,
            organization=None
        )
        unit.save()
        assert unit.organization == entrance.organization
