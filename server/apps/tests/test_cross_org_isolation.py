"""Cross-org isolation regression tests.

Multi-tenant safety: a user (or staff) belonging to Organization A must
never see or touch rows belonging to Organization B through any of the
public list / detail / admin endpoints.

This suite locks down the endpoints that were fixed in the `sec-fix-org-scoping`
branch (April 2026):

Apartments app
    * ``GET  /api/v1/apartments/buildings/``          BuildingListAPIView
    * ``GET  /api/v1/apartments/buildings/<id>/entrances/`` EntranceListAPIView
    * ``GET  /api/v1/apartments/buildings/<id>/units/``     UnitsByBuildingListAPIView
    * ``GET  /api/v1/apartments/buildings/admin/``    AdminBuildingListCreateAPIView
    * ``GET  /api/v1/apartments/buildings/<pkid>/``   BuildingUpdateDestroyAPIView

Profiles app
    * ``GET  /api/v1/profiles/all/``                  ProfileListAPIView
    * ``GET  /api/v1/profiles/non-tenant-profiles/``  NonTenantProfileListAPIView
    * ``GET  /api/v1/profiles/admin/all/``            ProfileAdminListAPIView
    * ``GET  /api/v1/profiles/admin/<slug>/update/``  ProfileAdminUpdateAPIView

Posts app (slug / tag / top endpoints)
    * ``GET  /api/v1/posts/<slug>/``                  PostDetailAPIView
    * ``GET  /api/v1/posts/popular-tags/``            PopularTagsListAPIView
    * ``GET  /api/v1/posts/top-posts/``               TopPostsListAPIView
    * ``GET  /api/v1/posts/posts-by-tag/<tag>/``      PostsByTagListAPIView

Every assertion uses ``resp.json()`` against the ``GenericJSONRenderer``
envelope (``{object_label: <payload>}``).
"""
from __future__ import annotations

from uuid import uuid4

import pytest
from rest_framework.test import APIClient

from apps.apartments.models import Building
from apps.organizations.models import Organization, OrganizationMembership, OrgRole
from apps.posts.models import Post
from apps.tests.factories import (
    AdminUserFactory,
    BuildingFactory,
    EntranceFactory,
    UnitFactory,
    UserFactory,
)


pytestmark = pytest.mark.django_db


# ── Factories / helpers ──────────────────────────────────────────────────────

def make_org(slug_prefix: str = "org") -> Organization:
    suffix = uuid4().hex[:6]
    return Organization.objects.create(
        name=f"Org-{suffix}",
        slug=f"{slug_prefix}-{suffix}",
        is_active=True,
    )


def add_membership(user, org, role: str = OrgRole.RESIDENT, is_active: bool = True):
    return OrganizationMembership.objects.create(
        user=user,
        organization=org,
        role=role,
        is_active=is_active,
    )


def make_post(author, organization: Organization, title: str = "P", tags=()) -> Post:
    post = Post.objects.create(
        author=author,
        title=f"{title}-{uuid4().hex[:4]}",
        body="body",
        organization=organization,
    )
    if tags:
        post.tags.add(*tags)
    return post


def _results(payload):
    """Unwrap paginated OR flat list payloads into a list of dicts."""
    if isinstance(payload, dict):
        return payload.get("results", [])
    return payload or []


def _client(user) -> APIClient:
    c = APIClient()
    c.force_authenticate(user=user)
    return c


# ── Fixtures: two isolated organisations with a tenant, a staff, and content ──

@pytest.fixture
def org_a():
    return make_org("a")


@pytest.fixture
def org_b():
    return make_org("b")


@pytest.fixture
def user_a(org_a):
    u = UserFactory(username=f"ua-{uuid4().hex[:4]}")
    add_membership(u, org_a)
    return u


@pytest.fixture
def user_b(org_b):
    u = UserFactory(username=f"ub-{uuid4().hex[:4]}")
    add_membership(u, org_b)
    return u


@pytest.fixture
def staff_a(org_a):
    u = UserFactory(username=f"sa-{uuid4().hex[:4]}")
    u.is_staff = True
    u.save(update_fields=["is_staff"])
    add_membership(u, org_a, role=OrgRole.ADMIN)
    return u


@pytest.fixture
def staff_b(org_b):
    u = UserFactory(username=f"sb-{uuid4().hex[:4]}")
    u.is_staff = True
    u.save(update_fields=["is_staff"])
    add_membership(u, org_b, role=OrgRole.ADMIN)
    return u


@pytest.fixture
def superuser():
    return AdminUserFactory(username=f"super-{uuid4().hex[:4]}")


@pytest.fixture
def building_a(org_a):
    return BuildingFactory(name=f"A-{uuid4().hex[:4]}", organization=org_a)


@pytest.fixture
def building_b(org_b):
    return BuildingFactory(name=f"B-{uuid4().hex[:4]}", organization=org_b)


@pytest.fixture
def entrance_a(building_a):
    return EntranceFactory(building=building_a, name="1")


@pytest.fixture
def entrance_b(building_b):
    return EntranceFactory(building=building_b, name="1")


@pytest.fixture
def unit_a(entrance_a):
    return UnitFactory(entrance=entrance_a, number="10")


@pytest.fixture
def unit_b(entrance_b):
    return UnitFactory(entrance=entrance_b, number="20")


# ── Apartments: Building list ────────────────────────────────────────────────

class TestBuildingList:
    URL = "/api/v1/apartments/buildings/"

    def test_unauthenticated_rejected(self, building_a):
        resp = APIClient().get(self.URL)
        assert resp.status_code == 401

    def test_user_a_sees_only_own_building(self, user_a, building_a, building_b):
        resp = _client(user_a).get(self.URL)
        assert resp.status_code == 200
        ids = {b["id"] for b in _results(resp.json()["buildings"])}
        assert str(building_a.id) in ids
        assert str(building_b.id) not in ids

    def test_user_b_sees_only_own_building(self, user_b, building_a, building_b):
        resp = _client(user_b).get(self.URL)
        assert resp.status_code == 200
        ids = {b["id"] for b in _results(resp.json()["buildings"])}
        assert str(building_b.id) in ids
        assert str(building_a.id) not in ids

    def test_superuser_sees_all(self, superuser, building_a, building_b):
        resp = _client(superuser).get(self.URL)
        assert resp.status_code == 200
        ids = {b["id"] for b in _results(resp.json()["buildings"])}
        assert str(building_a.id) in ids
        assert str(building_b.id) in ids


# ── Apartments: Entrance list (nested under building) ────────────────────────

class TestEntranceList:
    URL = "/api/v1/apartments/buildings/{bid}/entrances/"

    def test_user_a_sees_entrances_of_own_building(
        self, user_a, building_a, entrance_a
    ):
        resp = _client(user_a).get(self.URL.format(bid=building_a.id))
        assert resp.status_code == 200
        ids = {e["id"] for e in _results(resp.json()["entrances"])}
        assert str(entrance_a.id) in ids

    def test_user_a_gets_empty_for_building_b(
        self, user_a, building_b, entrance_b
    ):
        resp = _client(user_a).get(self.URL.format(bid=building_b.id))
        # Scoping drops the entrance silently — empty list, no 404 leak.
        assert resp.status_code == 200
        assert _results(resp.json()["entrances"]) == []


# ── Apartments: Units-by-building ────────────────────────────────────────────

class TestUnitsByBuilding:
    URL = "/api/v1/apartments/buildings/{bid}/units/"

    def test_user_a_sees_units_of_own_building(self, user_a, building_a, unit_a):
        resp = _client(user_a).get(self.URL.format(bid=building_a.id))
        assert resp.status_code == 200
        ids = {u["id"] for u in _results(resp.json()["units"])}
        assert str(unit_a.id) in ids

    def test_user_a_blind_to_building_b_units(
        self, user_a, building_b, unit_b
    ):
        resp = _client(user_a).get(self.URL.format(bid=building_b.id))
        assert resp.status_code == 200
        assert _results(resp.json()["units"]) == []


# ── Apartments: Admin CRUD on buildings ──────────────────────────────────────

class TestAdminBuildingCRUD:
    LIST_URL = "/api/v1/apartments/buildings/admin/"

    @staticmethod
    def _detail_url(pkid: int) -> str:
        return f"/api/v1/apartments/buildings/{pkid}/"

    def test_staff_a_cannot_list_building_b(
        self, staff_a, building_a, building_b
    ):
        resp = _client(staff_a).get(self.LIST_URL)
        assert resp.status_code == 200
        ids = {b["id"] for b in _results(resp.json()["buildings"])}
        assert str(building_a.id) in ids
        assert str(building_b.id) not in ids

    def test_staff_a_cannot_retrieve_building_b(self, staff_a, building_b):
        resp = _client(staff_a).get(self._detail_url(building_b.pkid))
        assert resp.status_code == 404

    def test_staff_a_cannot_patch_building_b(self, staff_a, building_b):
        resp = _client(staff_a).patch(
            self._detail_url(building_b.pkid),
            {"name": "hijacked"},
            format="json",
        )
        assert resp.status_code == 404
        building_b.refresh_from_db()
        assert building_b.name != "hijacked"

    def test_staff_a_cannot_delete_building_b(self, staff_a, building_b):
        resp = _client(staff_a).delete(self._detail_url(building_b.pkid))
        assert resp.status_code == 404
        assert Building.objects.filter(pkid=building_b.pkid).exists()


# ── Profiles: admin list endpoints ──────────────────────────────────────────

class TestProfileScoping:
    TENANT_LIST = "/api/v1/profiles/all/"
    NON_TENANT_LIST = "/api/v1/profiles/non-tenant-profiles/"
    ADMIN_LIST = "/api/v1/profiles/admin/all/"

    @staticmethod
    def _admin_update_url(slug: str) -> str:
        return f"/api/v1/profiles/admin/{slug}/update/"

    def test_staff_a_cannot_list_profiles_from_org_b(
        self, staff_a, user_a, user_b
    ):
        resp = _client(staff_a).get(self.TENANT_LIST)
        assert resp.status_code == 200
        slugs = {p["slug"] for p in _results(resp.json()["profiles"])}
        assert user_a.profile.slug in slugs
        assert user_b.profile.slug not in slugs

    def test_staff_a_admin_all_hides_org_b(
        self, staff_a, user_a, user_b
    ):
        resp = _client(staff_a).get(self.ADMIN_LIST)
        assert resp.status_code == 200
        slugs = {p["slug"] for p in _results(resp.json()["profiles"])}
        assert user_a.profile.slug in slugs
        assert user_b.profile.slug not in slugs

    def test_staff_a_cannot_retrieve_profile_from_org_b(
        self, staff_a, user_b
    ):
        resp = _client(staff_a).get(
            self._admin_update_url(user_b.profile.slug)
        )
        assert resp.status_code == 404

    def test_staff_a_cannot_patch_profile_from_org_b(
        self, staff_a, user_b
    ):
        resp = _client(staff_a).patch(
            self._admin_update_url(user_b.profile.slug),
            {"gender": "other"},
            format="json",
        )
        assert resp.status_code == 404


# ── Posts: slug detail / tags / top ──────────────────────────────────────────

class TestPostScoping:
    @staticmethod
    def _detail(slug: str) -> str:
        return f"/api/v1/posts/{slug}/"

    POPULAR_TAGS = "/api/v1/posts/popular-tags/"
    TOP_POSTS = "/api/v1/posts/top-posts/"

    @staticmethod
    def _by_tag(tag: str) -> str:
        return f"/api/v1/posts/tags/{tag}/"

    def test_user_a_cannot_retrieve_post_b_by_slug(
        self, user_a, user_b, org_b
    ):
        post_b = make_post(user_b, org_b, title="secret")
        resp = _client(user_a).get(self._detail(post_b.slug))
        assert resp.status_code == 404

    def test_user_a_cannot_see_tags_from_org_b(
        self, user_a, user_b, org_b
    ):
        make_post(user_b, org_b, title="t", tags=["secrettag"])
        resp = _client(user_a).get(self.POPULAR_TAGS)
        assert resp.status_code == 200
        body = resp.json()
        tags = body.get("popular_tags") or body.get("popular-tags") or body
        tag_names = {t["name"] for t in _results(tags)}
        assert "secrettag" not in tag_names

    def test_user_a_top_posts_excludes_org_b(
        self, user_a, user_b, org_a, org_b
    ):
        post_a = make_post(user_a, org_a, title="a-top")
        post_b = make_post(user_b, org_b, title="b-top")
        resp = _client(user_a).get(self.TOP_POSTS)
        assert resp.status_code == 200
        body = resp.json()
        payload = body.get("top_posts") or body.get("top-posts") or body
        slugs = {p["slug"] for p in _results(payload)}
        assert post_a.slug in slugs
        assert post_b.slug not in slugs

    def test_posts_by_tag_is_scoped_to_caller_org(
        self, user_a, user_b, org_a, org_b
    ):
        post_a = make_post(user_a, org_a, title="a-tag", tags=["shared"])
        post_b = make_post(user_b, org_b, title="b-tag", tags=["shared"])
        resp = _client(user_a).get(self._by_tag("shared"))
        assert resp.status_code == 200
        body = resp.json()
        payload = (
            body.get("posts_by_tag")
            or body.get("posts-by-tag")
            or body.get("posts")
            or body
        )
        slugs = {p["slug"] for p in _results(payload)}
        assert post_a.slug in slugs
        assert post_b.slug not in slugs
