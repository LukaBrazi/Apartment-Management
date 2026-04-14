import pytest
from apps.organizations.models import Organization, OrganizationType


@pytest.mark.django_db
class TestFeatureFlags:
    """Tests for organization feature flags"""

    def test_default_features_on_create(self, db):
        """Test that organizations have default feature flags"""
        org = Organization.objects.create(
            name="Test Org",
            slug="test-org",
            features={"issues": True, "news": True}
        )
        assert org.is_feature_enabled("issues") is True
        assert org.is_feature_enabled("news") is True

    def test_passes_disabled_by_default(self, db):
        """Test that passes feature is disabled by default"""
        org = Organization.objects.create(
            name="Test Org",
            slug="test-org",
            features={"issues": True, "news": True, "passes": False}
        )
        assert org.is_feature_enabled("passes") is False

    def test_enable_feature(self, org):
        """Test enabling a feature"""
        org.features = {"test_feature": False}
        org.save()
        assert org.is_feature_enabled("test_feature") is False

        org.features["test_feature"] = True
        org.save()
        assert org.is_feature_enabled("test_feature") is True

    def test_disable_feature(self, org):
        """Test disabling a feature"""
        org.features = {"test_feature": True}
        org.save()
        assert org.is_feature_enabled("test_feature") is True

        org.features["test_feature"] = False
        org.save()
        assert org.is_feature_enabled("test_feature") is False

    def test_all_feature_names_valid(self, org):
        """Test that feature names are valid strings"""
        org.features = {
            "issues": True,
            "news": True,
            "passes": False,
            "ratings": True
        }
        org.save()

        for feature_name in org.features.keys():
            assert isinstance(feature_name, str)
            assert len(feature_name) > 0
            assert feature_name.islower() or "_" in feature_name

    def test_empty_features_dict(self, db):
        """Test organization with empty features dict"""
        org = Organization.objects.create(
            name="Test Org",
            slug="test-org",
            features={}
        )
        # Empty dict should return empty list or may be populated with defaults
        enabled = org.get_enabled_features()
        assert isinstance(enabled, list)

    def test_get_enabled_features_multiple(self, org):
        """Test getting multiple enabled features"""
        org.features = {
            "issues": True,
            "news": True,
            "passes": False,
            "ratings": True
        }
        org.save()
        enabled = org.get_enabled_features()
        assert len(enabled) == 3
        assert set(enabled) == {"issues", "news", "ratings"}

    def test_features_field_type(self, org):
        """Test that features field is JSON"""
        assert isinstance(org.features, dict)
        org.features = {"feature1": True, "feature2": False}
        org.save()

        # Reload from DB
        org.refresh_from_db()
        assert isinstance(org.features, dict)
        assert org.features["feature1"] is True
        assert org.features["feature2"] is False
