# News Feature Design — 2026-03-12

## Context

Alpha Apartments (ОСББ portal) has an existing `Announcement` model scoped to a specific building. The goal is to add a separate, portal-wide **News** feature alongside it — not replacing it. Navigation label "Оголошення" → "Новини", pointing to the new `/news` route.

This is the core of the platform. Future features will attach as microservices.

---

## Decision

Keep `Announcement` (building-scoped, admin → tenants of that building).
Add `News` (portal-wide, admin-authored articles for all users).

---

## Backend — `apps/news/`

### Models

```python
class NewsCategory(TimeStampedModel):
    name   = CharField(100)
    slug   = AutoSlugField(populate_from="name", unique=True)
    color  = CharField(7, default="#2F6FED")  # hex color for UI badge

class News(TimeStampedModel):
    title        = CharField(255)
    slug         = AutoSlugField(populate_from="title", unique=True)
    excerpt      = TextField()           # short description for card
    body         = TextField()           # full article body
    cover_image  = ImageField(nullable)  # → MinIO
    category     = FK → NewsCategory (nullable, SET_NULL)
    tags         = TaggableManager       # taggit
    author       = FK → User (CASCADE)
    published_at = DateTimeField(nullable)
    is_published = BooleanField(default=False)
    pinned       = BooleanField(default=False)
    views_count  = PositiveIntegerField(default=0)
    external_url = URLField(blank=True)

    class Meta:
        ordering = ["-pinned", "-published_at"]
```

### API Endpoints (`/api/v1/news/`)

| Endpoint | Method | Permission | Renderer label |
|----------|--------|------------|----------------|
| `/api/v1/news/` | GET | IsAuthenticated | `news` (list, no pagination) |
| `/api/v1/news/<slug>/` | GET | IsAuthenticated | `news_item` |
| `/api/v1/news/admin/` | GET, POST | IsAdminUser | `news` |
| `/api/v1/news/admin/<slug>/` | GET, PATCH, DELETE | IsAdminUser | `news_item` |

- List endpoint: only `is_published=True`, ordered by `-pinned, -published_at`
- Detail endpoint: increments `views_count` on each GET
- Admin list: all news (including drafts)

### Files to create
```
server/apps/news/
  __init__.py
  apps.py
  models.py
  serializers.py
  views.py
  urls.py
  admin.py
  migrations/
    __init__.py
    0001_initial.py
```

Add to `INSTALLED_APPS`: `"apps.news"`
Add to `config/urls.py`: `path("api/v1/news/", include("apps.news.urls"))`

---

## Frontend

### Navigation (`constants/index.ts`)
```ts
// Before: { path: "/announcements", label: "Оголошення", ... }
// After:
{ path: "/news", label: "Новини", imgLocation: "/assets/icons/speak.svg" }
```

### New Pages
```
client/src/app/(estate)/news/
  page.tsx        — news list (cards: cover, badge, title, excerpt, date, 📌 pin)
  [slug]/
    page.tsx      — news detail (cover, body, tags, external_url, views_count)
```

### Admin Page
```
client/src/app/admin/news/page.tsx  — table + inline create/edit/delete form
```
Add to admin nav layout: `{ path: "/admin/news", label: "Новини", icon: Newspaper }`

### Redux
```
client/src/lib/redux/features/news/newsApiSlice.ts
  - getNews         (query, authenticated)
  - getNewsItem     (query by slug)
  - adminCreateNews (mutation)
  - adminUpdateNews (mutation)
  - adminDeleteNews (mutation)
```

### ComingSoon Component
Replace all hardcoded "В розробці" strings with:
```tsx
<ComingSoon serviceName="Payments" microserviceKey="PAYMENTS_SERVICE_URL" />
```
Component reads `process.env.NEXT_PUBLIC_{microserviceKey}` — if set, renders iframe/link; if not, renders placeholder. Microservice-ready by design.

Affected pages: `payments/page.tsx`, `contacts/page.tsx`

---

## Tests

### Unit (`server/apps/tests/test_news.py`)
- NewsCategory model creation
- News model creation (published/draft)
- Pinned news appears first in list
- Only published news visible to authenticated non-admin
- Admin sees all (including drafts)
- views_count increments on detail GET
- Tenant cannot create/edit news
- Admin can create, update, delete news
- external_url is optional

### E2E (`sckandi-e2e/tests/functional/news-flow.spec.ts`)
- `/news` page loads without error
- News card visible with title
- Clicking card navigates to `/news/[slug]`
- Detail page shows title and body
- Admin can create a news item → appears in list

---

## Naming / Cleanup
- Nav: "Оголошення" → "Новини"
- URL: `/announcements` → `/news` (nav only; `/announcements` page file can stay for building announcements via API, but is no longer linked from nav)
- README: rewrite to reflect current state, News feature, microservices-ready architecture
- TODO.md: mark completed items, add News as done, remove stale items

---

## Commits
```bash
# Main repo
git commit -m "feat(news): add News model + API + /news frontend + ComingSoon + rename nav"

# E2E repo
git commit -m "feat(e2e): add news-flow tests"
```

---

## Microservices Readiness

All "in development" pages use `<ComingSoon microserviceKey="..." />`. When a microservice is ready:
1. Set `NEXT_PUBLIC_{KEY}_URL=https://service.example.com` in env
2. Component automatically connects — no code change needed

This pattern ensures the core portal is cleanly separated from future services.
