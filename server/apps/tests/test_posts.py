"""
Hardcore tests for Posts/Replies/Bookmarks/Upvotes.

Scope: apps.posts.views — this module has **zero** unit-test coverage today.
The e2e suite was our only safety net for PostSerializer.create() org
auto-binding, `CanCreateEditPost`, author-only edit guard, bookmark
idempotency, and F()-expression upvote increments. With e2e now off CI
(2026-04-18), these tests are the line of defence.

Invariants asserted:
- PostListAPIView (AllowAny): anonymous and non-member authenticated users
  see all posts; authenticated users who are members of an org see ONLY
  posts in their org(s); superuser bypasses the org filter.
- PostCreateAPIView: `CanCreateEditPost` allows superuser/staff/tenant,
  denies guest (401) and non-tenant worker (403). Created post is
  auto-bound to the caller's primary organization.
- PostUpdateAPIView: non-authors get 403; authors can PATCH body/tags.
- BookmarkPostAPIView: first PATCH → 200, duplicate → 400.
- UnbookmarkPostAPIView: on a bookmarked post → 200, on an un-bookmarked
  post → 400.
- UpvotePostAPIView: first PATCH → 200 AND `upvotes` increments exactly
  by 1 (no double-count on repeat — F()-expression path is idempotent
  via `upvoted_by` M2M).
- DownvotePostAPIView: downvote removes existing upvote and adds a
  downvote (toggle semantics on repeat call).
- ReplyCreateAPIView: auto-sets author and post from URL kwarg.
- ReplyListAPIView: ordered by -created_at, filtered by post_id.
- MyPostListAPIView: scoped to request.user.author only.

All assertions are **exact** — status codes, counts, and values. No
`status_code in [200, 201]` and no `is not None` guards.
"""
import pytest
from rest_framework.test import APIClient

from apps.organizations.models import Organization, OrganizationMembership
from apps.posts.models import Post, Reply
from apps.profiles.models import Profile
from apps.tests.factories import AdminUserFactory, UserFactory


# ── URL constants ────────────────────────────────────────────────────────────

LIST_URL = "/api/v1/posts/all/"
CREATE_URL = "/api/v1/posts/create/"
MY_POSTS_URL = "/api/v1/posts/my-posts/"
BOOKMARKED_URL = "/api/v1/posts/bookmarked/posts/"


def _detail_url(slug: str) -> str:
    return f"/api/v1/posts/{slug}/"


def _update_url(slug: str) -> str:
    return f"/api/v1/posts/{slug}/update/"


def _bookmark_url(slug: str) -> str:
    return f"/api/v1/posts/{slug}/bookmark/"


def _unbookmark_url(slug: str) -> str:
    return f"/api/v1/posts/{slug}/unbookmark/"


def _upvote_url(post_id) -> str:
    return f"/api/v1/posts/{post_id}/upvote/"


def _downvote_url(post_id) -> str:
    return f"/api/v1/posts/{post_id}/downvote/"


def _reply_create_url(post_id) -> str:
    return f"/api/v1/posts/{post_id}/reply/"


def _reply_list_url(post_id) -> str:
    return f"/api/v1/posts/{post_id}/replies/"


# ── Helpers ──────────────────────────────────────────────────────────────────

def make_post(author, title="Test Post", body="body", organization=None) -> Post:
    """Create a Post directly (bypasses serializer) for test arrangement.

    `Post.save()` enforces author must be tenant/staff/superuser — the
    default UserFactory yields a TENANT profile so plain users work.
    """
    return Post.objects.create(
        author=author,
        title=title,
        body=body,
        organization=organization,
    )


def make_org(slug="org") -> Organization:
    # Sequence-ize to avoid slug collisions across parametrized tests
    from uuid import uuid4

    suffix = uuid4().hex[:6]
    return Organization.objects.create(
        name=f"Org-{suffix}",
        slug=f"{slug}-{suffix}",
        is_active=True,
    )


def add_membership(user, org) -> OrganizationMembership:
    return OrganizationMembership.objects.create(
        user=user,
        organization=org,
        is_active=True,
    )


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def tenant():
    # Default factory creates a user whose profile.occupation == TENANT.
    u = UserFactory(username="post_tenant")
    assert u.profile.occupation == Profile.Occupation.TENANT
    return u


@pytest.fixture
def tenant_client(tenant):
    c = APIClient()
    c.force_authenticate(user=tenant)
    c.user = tenant
    return c


@pytest.fixture
def other_tenant():
    u = UserFactory(username="post_other_tenant")
    assert u.profile.occupation == Profile.Occupation.TENANT
    return u


@pytest.fixture
def other_tenant_client(other_tenant):
    c = APIClient()
    c.force_authenticate(user=other_tenant)
    c.user = other_tenant
    return c


@pytest.fixture
def worker():
    """A non-tenant, non-staff user — CanCreateEditPost must reject."""
    u = UserFactory(username="post_worker")
    u.profile.occupation = Profile.Occupation.PLUMBER
    u.profile.save()
    return u


@pytest.fixture
def worker_client(worker):
    c = APIClient()
    c.force_authenticate(user=worker)
    c.user = worker
    return c


@pytest.fixture
def superuser():
    return AdminUserFactory(username="post_super")


@pytest.fixture
def superuser_client(superuser):
    c = APIClient()
    c.force_authenticate(user=superuser)
    c.user = superuser
    return c


# ═════════════════════════════════════════════════════════════════════════════
# PostListAPIView — org-scoping + AllowAny
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestPostList:
    def test_anonymous_sees_all_posts_no_org_filter(self, api_client, tenant, other_tenant):
        """AllowAny: unauthenticated caller sees every post (no org filter applied)."""
        org_a = make_org("orga")
        org_b = make_org("orgb")
        make_post(tenant, title="A-post", organization=org_a)
        make_post(other_tenant, title="B-post", organization=org_b)
        make_post(tenant, title="No-org-post", organization=None)

        resp = api_client.get(LIST_URL)
        assert resp.status_code == 200, resp.content

        results = resp.json()["posts"]["results"]
        titles = {r["title"] for r in results}
        assert titles == {"A-post", "B-post", "No-org-post"}, (
            f"Anonymous must see all 3 posts regardless of org. Got: {titles}"
        )

    def test_authenticated_member_sees_only_own_org(
        self, tenant, other_tenant, tenant_client
    ):
        """Non-superuser with org membership sees ONLY posts in their org."""
        org_a = make_org("own")
        org_b = make_org("other")
        add_membership(tenant, org_a)

        mine = make_post(tenant, title="mine", organization=org_a)
        make_post(other_tenant, title="other", organization=org_b)
        make_post(tenant, title="ghost", organization=None)  # no org → excluded

        resp = tenant_client.get(LIST_URL)
        assert resp.status_code == 200, resp.content

        results = resp.json()["posts"]["results"]
        titles = [r["title"] for r in results]
        assert titles == ["mine"], (
            f"Expected exactly ['mine'], got {titles}. Org scoping must "
            f"exclude other orgs AND organization=NULL rows."
        )
        assert results[0]["id"] == str(mine.id)

    def test_authenticated_without_membership_sees_all(self, tenant, other_tenant, tenant_client):
        """Backward-compat: user with zero memberships is NOT filtered."""
        org_a = make_org("unused")
        make_post(tenant, title="p1", organization=org_a)
        make_post(other_tenant, title="p2", organization=None)

        # tenant has NO OrganizationMembership rows
        assert tenant.organization_memberships.count() == 0

        resp = tenant_client.get(LIST_URL)
        assert resp.status_code == 200

        results = resp.json()["posts"]["results"]
        titles = sorted(r["title"] for r in results)
        assert titles == ["p1", "p2"], (
            f"User with no memberships should see all posts. Got: {titles}"
        )

    def test_superuser_bypasses_org_filter(
        self, tenant, other_tenant, superuser, superuser_client
    ):
        """Superuser with membership in Org-A still sees Org-B posts."""
        org_a = make_org("sa")
        org_b = make_org("sb")
        add_membership(superuser, org_a)

        make_post(tenant, title="in-a", organization=org_a)
        make_post(other_tenant, title="in-b", organization=org_b)

        resp = superuser_client.get(LIST_URL)
        assert resp.status_code == 200

        titles = {r["title"] for r in resp.json()["posts"]["results"]}
        assert titles == {"in-a", "in-b"}, (
            f"Superuser must see BOTH orgs. Got: {titles}"
        )


# ═════════════════════════════════════════════════════════════════════════════
# PostCreateAPIView — permission gate + org auto-bind
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestPostCreate:
    PAYLOAD = {
        "title": "Hello World",
        "body": "A new post.",
        "tags": ["news", "urgent"],
    }

    def test_anonymous_gets_401(self, api_client):
        resp = api_client.post(CREATE_URL, self.PAYLOAD, format="json")
        assert resp.status_code == 401, (
            f"Anonymous post create must be 401 (IsAuthenticated fails first). "
            f"Got {resp.status_code}: {resp.data}"
        )

    def test_worker_gets_403(self, worker_client):
        """Non-tenant worker (plumber) is rejected by CanCreateEditPost."""
        resp = worker_client.post(CREATE_URL, self.PAYLOAD, format="json")
        assert resp.status_code == 403, (
            f"Worker occupation must be rejected with 403 by CanCreateEditPost. "
            f"Got {resp.status_code}: {resp.data}"
        )

    def test_tenant_creates_post(self, tenant_client, tenant):
        resp = tenant_client.post(CREATE_URL, self.PAYLOAD, format="json")
        assert resp.status_code == 201, (
            f"Tenant must be able to create posts. Got {resp.status_code}: {resp.data}"
        )
        body = resp.json()["post"]
        assert body["title"] == "Hello World"
        assert body["author_username"] == tenant.username
        assert sorted(body["tags"]) == ["news", "urgent"]
        # Persisted
        assert Post.objects.filter(author=tenant, title="Hello World").count() == 1

    def test_superuser_creates_post(self, superuser_client, superuser):
        resp = superuser_client.post(CREATE_URL, self.PAYLOAD, format="json")
        assert resp.status_code == 201, resp.data
        assert Post.objects.filter(author=superuser).count() == 1

    def test_staff_creates_post(self):
        staff = UserFactory(username="post_staff", is_staff=True)
        client = APIClient()
        client.force_authenticate(user=staff)
        resp = client.post(CREATE_URL, self.PAYLOAD, format="json")
        assert resp.status_code == 201, resp.data

    def test_created_post_auto_bound_to_primary_org(self, tenant_client, tenant):
        """PostSerializer.create() auto-binds organization when caller is a member."""
        org = make_org("autoorg")
        add_membership(tenant, org)

        resp = tenant_client.post(CREATE_URL, self.PAYLOAD, format="json")
        assert resp.status_code == 201, resp.data

        post = Post.objects.get(author=tenant)
        assert post.organization_id == org.pk, (
            f"Post must auto-bind to caller's primary org. Expected {org.pk}, "
            f"got {post.organization_id}."
        )

    def test_created_post_has_null_org_when_caller_has_none(self, tenant_client, tenant):
        """No memberships → organization=None (backward compat, not a crash)."""
        assert tenant.organization_memberships.count() == 0
        resp = tenant_client.post(CREATE_URL, self.PAYLOAD, format="json")
        assert resp.status_code == 201, resp.data
        post = Post.objects.get(author=tenant)
        assert post.organization is None

    def test_missing_title_rejected_400(self, tenant_client):
        resp = tenant_client.post(
            CREATE_URL,
            {"body": "no title", "tags": []},
            format="json",
        )
        assert resp.status_code == 400
        assert "title" in resp.data


# ═════════════════════════════════════════════════════════════════════════════
# PostUpdateAPIView — author-only edit
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestPostUpdate:
    def test_author_can_patch_body(self, tenant_client, tenant):
        post = make_post(tenant, title="Orig", body="orig body")
        resp = tenant_client.patch(
            _update_url(post.slug),
            {"body": "new body", "tags": ["edited"]},
            format="json",
        )
        assert resp.status_code == 200, resp.data
        post.refresh_from_db()
        assert post.body == "new body"
        assert sorted(t.name for t in post.tags.all()) == ["edited"]

    def test_non_author_gets_403(self, tenant, other_tenant_client):
        """Different tenant editing someone else's post → PermissionDenied."""
        post = make_post(tenant, title="Locked")
        resp = other_tenant_client.patch(
            _update_url(post.slug),
            {"body": "hacked"},
            format="json",
        )
        assert resp.status_code == 403, (
            f"Non-author edit must be 403. Got {resp.status_code}: {resp.data}"
        )
        post.refresh_from_db()
        assert post.body == "body", "Body was mutated by non-author!"

    def test_anonymous_gets_401(self, api_client, tenant):
        post = make_post(tenant, title="Guarded")
        resp = api_client.patch(
            _update_url(post.slug),
            {"body": "x"},
            format="json",
        )
        assert resp.status_code == 401

    def test_worker_gets_403_on_own_post_from_db(self, worker, worker_client):
        """
        Even if a non-tenant worker somehow got a post row into the DB
        (e.g. seeded), CanCreateEditPost must deny them at the gate.

        Bypass Post.save()'s tenant guard by updating after-the-fact — the
        occupation change is what makes the worker ineligible at update time.
        """
        # Create while still tenant
        worker.profile.occupation = Profile.Occupation.TENANT
        worker.profile.save()
        post = make_post(worker, title="Demote me")
        # Now demote to plumber
        worker.profile.occupation = Profile.Occupation.PLUMBER
        worker.profile.save()

        resp = worker_client.patch(
            _update_url(post.slug),
            {"body": "try edit"},
            format="json",
        )
        assert resp.status_code == 403


# ═════════════════════════════════════════════════════════════════════════════
# BookmarkPostAPIView / UnbookmarkPostAPIView
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestBookmark:
    def test_bookmark_first_call_returns_200(self, tenant_client, tenant):
        post = make_post(tenant, title="B1")
        resp = tenant_client.patch(_bookmark_url(post.slug))
        assert resp.status_code == 200
        assert resp.json()["message"] == "Post bookmarked successfully."
        assert post.bookmarked_by.filter(pk=tenant.pk).exists()

    def test_bookmark_duplicate_returns_400(self, tenant_client, tenant):
        post = make_post(tenant, title="B2")
        r1 = tenant_client.patch(_bookmark_url(post.slug))
        assert r1.status_code == 200
        r2 = tenant_client.patch(_bookmark_url(post.slug))
        assert r2.status_code == 400, (
            f"Duplicate bookmark must be 400, got {r2.status_code}: {r2.data}"
        )
        assert r2.json()["message"] == "Post already bookmarked."
        # Still only one M2M row
        assert post.bookmarked_by.filter(pk=tenant.pk).count() == 1

    def test_unbookmark_without_existing_returns_400(self, tenant_client, tenant):
        post = make_post(tenant, title="B3")
        resp = tenant_client.patch(_unbookmark_url(post.slug))
        assert resp.status_code == 400
        assert resp.json()["message"] == "Post not bookmarked."

    def test_bookmark_unbookmark_roundtrip(self, tenant_client, tenant):
        post = make_post(tenant, title="B4")
        assert tenant_client.patch(_bookmark_url(post.slug)).status_code == 200
        assert tenant_client.patch(_unbookmark_url(post.slug)).status_code == 200
        post.refresh_from_db()
        assert not post.bookmarked_by.filter(pk=tenant.pk).exists()

    def test_bookmarked_list_shows_only_own_bookmarks(
        self, tenant_client, tenant, other_tenant
    ):
        mine = make_post(tenant, title="mine-bm")
        theirs = make_post(other_tenant, title="theirs-bm")
        mine.bookmarked_by.add(tenant)
        theirs.bookmarked_by.add(other_tenant)  # not the caller

        resp = tenant_client.get(BOOKMARKED_URL)
        assert resp.status_code == 200, resp.content
        results = resp.json()["bookmarked_posts"]["results"]
        titles = [r["title"] for r in results]
        assert titles == ["mine-bm"], (
            f"BookmarkedPostsList must return ONLY caller's bookmarks. Got: {titles}"
        )


# ═════════════════════════════════════════════════════════════════════════════
# UpvotePostAPIView / DownvotePostAPIView — F() + M2M idempotency
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestVoting:
    def test_upvote_first_call_increments_by_one(self, tenant_client, tenant):
        post = make_post(tenant, title="U1")
        assert post.upvotes == 0

        resp = tenant_client.patch(_upvote_url(post.id))
        assert resp.status_code == 200, resp.data

        post.refresh_from_db()
        assert post.upvotes == 1, (
            f"First upvote must increment to 1 (F()+1). Got {post.upvotes}."
        )
        assert post.upvoted_by.filter(pk=tenant.pk).exists()

    def test_upvote_repeat_is_idempotent(self, tenant_client, tenant):
        """Second upvote from same user must NOT double-count.

        Serializer guards with `if user not in instance.upvoted_by.all()`.
        """
        post = make_post(tenant, title="U2")
        tenant_client.patch(_upvote_url(post.id))
        tenant_client.patch(_upvote_url(post.id))
        post.refresh_from_db()
        assert post.upvotes == 1, (
            f"Repeated upvote must stay at 1; M2M guard failed. Got {post.upvotes}."
        )
        assert post.upvoted_by.filter(pk=tenant.pk).count() == 1

    def test_upvote_different_users_accumulate(self, tenant_client, other_tenant_client, tenant):
        post = make_post(tenant, title="U3")
        tenant_client.patch(_upvote_url(post.id))
        other_tenant_client.patch(_upvote_url(post.id))
        post.refresh_from_db()
        assert post.upvotes == 2, (
            f"Two distinct users upvoting must yield 2. Got {post.upvotes}."
        )

    def test_upvote_missing_post_returns_404(self, tenant_client):
        from uuid import uuid4

        resp = tenant_client.patch(_upvote_url(uuid4()))
        assert resp.status_code == 404

    def test_upvote_anonymous_401(self, api_client, tenant):
        post = make_post(tenant, title="U4")
        resp = api_client.patch(_upvote_url(post.id))
        assert resp.status_code == 401

    def test_downvote_removes_existing_upvote(self, tenant_client, tenant):
        """Downvote by an already-upvoted user: upvote -1, downvote +1."""
        post = make_post(tenant, title="D1")
        tenant_client.patch(_upvote_url(post.id))
        post.refresh_from_db()
        assert post.upvotes == 1

        resp = tenant_client.patch(_downvote_url(post.id))
        assert resp.status_code == 200, resp.data

        post.refresh_from_db()
        assert post.upvotes == 0, (
            f"Downvote by an upvoter must remove the upvote (0). Got {post.upvotes}."
        )
        assert post.downvotes == 1, (
            f"Downvote must add a downvote (1). Got {post.downvotes}."
        )
        assert not post.upvoted_by.filter(pk=tenant.pk).exists()
        assert post.downvoted_by.filter(pk=tenant.pk).exists()


# ═════════════════════════════════════════════════════════════════════════════
# ReplyCreateAPIView / ReplyListAPIView
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestReplies:
    def test_reply_create_auto_sets_author_and_post(self, tenant_client, tenant):
        post = make_post(tenant, title="R1")
        resp = tenant_client.post(
            _reply_create_url(post.id),
            {"body": "great read"},
            format="json",
        )
        assert resp.status_code == 201, resp.data

        body = resp.json()["reply"]
        assert body["body"] == "great read"
        assert body["author_username"] == tenant.username

        # Exactly one reply persisted for this post, authored by tenant
        replies = Reply.objects.filter(post=post)
        assert replies.count() == 1
        r = replies.first()
        assert r.author_id == tenant.pk
        assert r.post_id == post.pk

    def test_reply_create_anonymous_401(self, api_client, tenant):
        post = make_post(tenant, title="R2")
        resp = api_client.post(
            _reply_create_url(post.id),
            {"body": "anon"},
            format="json",
        )
        assert resp.status_code == 401

    def test_reply_create_missing_post_returns_404(self, tenant_client):
        from uuid import uuid4

        resp = tenant_client.post(
            _reply_create_url(uuid4()),
            {"body": "nope"},
            format="json",
        )
        assert resp.status_code == 404

    def test_reply_list_ordered_newest_first(self, tenant_client, tenant):
        post = make_post(tenant, title="R3")
        r1 = Reply.objects.create(post=post, author=tenant, body="first")
        r2 = Reply.objects.create(post=post, author=tenant, body="second")
        r3 = Reply.objects.create(post=post, author=tenant, body="third")

        resp = tenant_client.get(_reply_list_url(post.id))
        assert resp.status_code == 200
        results = resp.json()["replies"]["results"]
        # Paginated; order must be -created_at so the newest appears first
        bodies = [r["body"] for r in results]
        assert bodies == ["third", "second", "first"], (
            f"Expected reverse-chronological order ['third','second','first'], "
            f"got {bodies}."
        )
        # Defensive: the rows we created are actually present (not some other
        # post's replies leaking in)
        assert {str(r1.id), str(r2.id), str(r3.id)} == {r["id"] for r in results}

    def test_reply_list_scoped_by_post_id(self, tenant_client, tenant):
        post_a = make_post(tenant, title="RA")
        post_b = make_post(tenant, title="RB")
        Reply.objects.create(post=post_a, author=tenant, body="in-A")
        Reply.objects.create(post=post_b, author=tenant, body="in-B")

        resp = tenant_client.get(_reply_list_url(post_a.id))
        assert resp.status_code == 200
        results = resp.json()["replies"]["results"]
        bodies = [r["body"] for r in results]
        assert bodies == ["in-A"], (
            f"Reply list must filter by post_id; got cross-post leakage: {bodies}"
        )


# ═════════════════════════════════════════════════════════════════════════════
# MyPostListAPIView — scoped to request.user
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestMyPosts:
    def test_my_posts_scoped_to_request_user(self, tenant_client, tenant, other_tenant):
        mine_a = make_post(tenant, title="mine-a")
        mine_b = make_post(tenant, title="mine-b")
        make_post(other_tenant, title="NOT-mine")

        resp = tenant_client.get(MY_POSTS_URL)
        assert resp.status_code == 200, resp.content
        titles = sorted(r["title"] for r in resp.json()["my_posts"]["results"])
        assert titles == ["mine-a", "mine-b"], (
            f"my-posts must only return caller's posts. Got: {titles}"
        )
        # Sanity: the "NOT-mine" post does exist globally — the filter is
        # what excludes it, not an empty DB.
        assert Post.objects.filter(title="NOT-mine").count() == 1

    def test_my_posts_anonymous_401(self, api_client):
        resp = api_client.get(MY_POSTS_URL)
        assert resp.status_code == 401


# ═════════════════════════════════════════════════════════════════════════════
# PostDetailAPIView — ContentView side-effect
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestPostDetail:
    def test_detail_records_content_view(self, tenant_client, tenant):
        """GET /posts/<slug>/ must create a ContentView row via get_or_create."""
        from django.contrib.contenttypes.models import ContentType

        from apps.common.models import ContentView

        post = make_post(tenant, title="View-tracked")
        ct = ContentType.objects.get_for_model(Post)

        before = ContentView.objects.filter(
            content_type=ct, object_id=post.pk
        ).count()

        resp = tenant_client.get(_detail_url(post.slug))
        assert resp.status_code == 200, resp.content
        assert resp.json()["post"]["slug"] == post.slug

        after = ContentView.objects.filter(
            content_type=ct, object_id=post.pk
        ).count()
        assert after == before + 1, (
            f"ContentView row must be created on detail GET. "
            f"before={before}, after={after}"
        )

    def test_detail_view_is_idempotent_per_user_ip(self, tenant_client, tenant):
        """Repeat GET by the same user must not duplicate ContentView (get_or_create)."""
        from django.contrib.contenttypes.models import ContentType

        from apps.common.models import ContentView

        post = make_post(tenant, title="once")
        ct = ContentType.objects.get_for_model(Post)

        tenant_client.get(_detail_url(post.slug))
        tenant_client.get(_detail_url(post.slug))

        count = ContentView.objects.filter(
            content_type=ct, object_id=post.pk, user=tenant
        ).count()
        assert count == 1, (
            f"get_or_create on (content_type, object_id, viewer_ip, user) "
            f"must de-duplicate. Got {count} rows."
        )

    def test_detail_missing_slug_returns_404(self, tenant_client):
        resp = tenant_client.get(_detail_url("does-not-exist"))
        assert resp.status_code == 404
