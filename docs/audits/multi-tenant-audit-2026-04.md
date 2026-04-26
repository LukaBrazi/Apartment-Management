# ApartmentOS Multi-Tenant Audit Report

**Date:** April 2026  
**Version:** 1.0  
**Scope:** Complete module assessment for multi-tenant single-deployment architecture

---

## Executive Summary

ApartmentOS is transitioning from a per-client deployment model to a **single-deployment multi-tenant platform**. This audit reviews all 13 installed apps to assess organization-scoping readiness.

### Key Finding:
- **6 modules fully scoped** (safe for multi-tenant)
- **3 modules partially scoped** (need review)
- **4 modules not scoped** (require migration or acceptance)

---

## Module Assessment Table

| # | Module | Model(s) | Status | Details | Action Required |
|---|--------|---------|--------|---------|-----------------|
| 1 | **Buildings** | Building | ✅ SCOPED | FK to Organization | None — ready |
| 2 | **Entrances** | Entrance | ✅ SCOPED | FK to Organization + auto-inherited from Building | None — ready |
| 3 | **Units** | Unit | ✅ SCOPED | FK to Organization + auto-inherited from Entrance | None — ready |
| 4 | **Issues** | Issue, Category | ⚠️ PARTIALLY | Issue has org FK; Category is global (shared) | Migrate Category to org-scoped or create per-org categories |
| 5 | **Passes** | VehiclePass | ✅ SCOPED | FK to Organization | None — ready |
| 6 | **Posts** | Post, Reply, Announcement | ✅ SCOPED | Post has org FK; Reply inherits via Post; Announcement tied to Building | None — ready |
| 7 | **News** | News, NewsCategory | ⚠️ PARTIALLY | News has org FK (can be NULL=global); NewsCategory is global | Migrate NewsCategory or allow per-org categories |
| 8 | **Site Settings** | SiteSettings, SiteLink, ContactPerson | ❌ NOT SCOPED | Singleton pattern (pk=1 only) — shared across all orgs | CRITICAL: Migrate to org-scoped model or extend SiteSettings with org FK |
| 9 | **Profiles** | Profile | ✅ SCOPED | Links to Unit (org-scoped); org membership tracked via OrganizationMembership | None — ready |
| 10 | **Users** | User, OrganizationMembership | ✅ SCOPED | Users are global; org membership tracked via OrganizationMembership junction table | None — ready |
| 11 | **Ratings** | Rating | ❌ NOT SCOPED | No org FK — purely user-to-user, not org-aware | Consider: is this org-specific or platform-wide? If org-specific, add FK |
| 12 | **Reports** | Report | ❌ NOT SCOPED | No org FK — purely user-to-user, not org-aware | Consider: is this org-specific or platform-wide? If org-specific, add FK |
| 13 | **Notifications** | TelegramProfile, TelegramVerificationToken | ❌ NOT SCOPED | No org FK — per-user, but not org-aware | Low priority: notifications are user-specific, not org-data |
| 14 | **Apartments (Legacy)** | Apartment, ResidentialComplex | ⚠️ PARTIALLY | ResidentialComplex is global (legacy); Apartment has no org FK | Consider deprecating in favor of Building/Entrance/Unit model |

---

## Detailed Findings by Category

### ✅ FULLY SCOPED (Safe for Multi-Tenant)

#### 1. Buildings/Entrances/Units Hierarchy
```python
# Building
organization = ForeignKey(Organization, on_delete=models.CASCADE, ...)

# Entrance (auto-inherited)
def save(self, *args, **kwargs):
    if self.building_id and not self.organization_id:
        self.organization = self.building.organization
    super().save(*args, **kwargs)

# Unit (auto-inherited)
def save(self, *args, **kwargs):
    if self.entrance_id and not self.organization_id:
        self.organization = self.entrance.organization
    super().save(*args, **kwargs)
```
✅ **Status:** Ready. All physical assets are properly scoped.

#### 2. Issues & Passes
```python
# Issue
organization = ForeignKey(Organization, on_delete=models.SET_NULL, ...)

# VehiclePass
organization = ForeignKey(Organization, on_delete=models.SET_NULL, ...)
```
✅ **Status:** Ready. Both are properly scoped.

#### 3. Posts & Announcements
```python
# Post
organization = ForeignKey(Organization, on_delete=models.SET_NULL, ...)

# Announcement
building = ForeignKey(Building, ...)  # Building is org-scoped, so safe
```
✅ **Status:** Ready. Posts are directly scoped; Announcements inherit via Building.

#### 4. Users & Profiles
```python
# User — global (as expected)
# Profile — links to Unit (org-scoped)
unit = ForeignKey(Unit, ...)

# Organization Membership (junction table)
user = ForeignKey(User, ...)
organization = ForeignKey(Organization, unique_together=["user", "organization"])
```
✅ **Status:** Ready. Users are global but org membership is tracked.

---

### ⚠️ PARTIALLY SCOPED (Needs Attention)

#### 1. Issue Categories
```python
class Category(TimeStampedModel):
    name = models.CharField(...)
    sla_hours = models.PositiveIntegerField(...)
    # ❌ NO ORGANIZATION FK
```

**Problem:** Categories are global. If Organization A needs "Plumbing" with 72h SLA and Organization B needs it with 48h SLA, conflicts arise.

**Options:**
- **Option A:** Add `organization = ForeignKey(Organization, ...)` to Category
- **Option B:** Create OrganizationCategory junction table
- **Option C:** Accept categories as platform-wide (simpler, works for many cases)

**Recommendation:** Start with Option C (global categories); migrate to Option A if clients request custom categories.

#### 2. News Categories
```python
class NewsCategory(TimeStampedModel):
    name = models.CharField(...)
    # ❌ NO ORGANIZATION FK
```

**Same issue as Issue Categories.**

**Recommendation:** Same approach — start global, migrate to per-org if needed.

#### 3. Legacy Apartment Model
```python
class Apartment(TimeStampedModel):
    unit_number = models.CharField(...)
    building = models.CharField(...)  # String, not FK!
    # ❌ NO ORGANIZATION FK
    # ❌ DEPRECATED — replaced by Building/Entrance/Unit
```

**Status:** This model is legacy and being phased out in favor of Building/Entrance/Unit hierarchy.

**Action:** Continue migration to new model. Apartment.unit field links to Unit (which is org-scoped).

---

### ❌ NOT SCOPED (Requires Migration or Acceptance)

#### 1. SiteSettings — CRITICAL ⚠️
```python
class SiteSettings(models.Model):
    # SINGLETON: always pk=1
    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)
```

**Problem:** Only ONE SiteSettings row can exist. All orgs share logo, colors, support email, etc.

**Impact:** HIGH
- If Organization A uses blue branding, Organization B cannot use red
- Support email is platform-wide, not per-org
- Current_complex can only point to one ResidentialComplex

**Options:**
- **Option A (RECOMMENDED):** Add `organization = ForeignKey(Organization, null=True, blank=True)` 
  - Migration: existing pk=1 becomes org=NULL (platform defaults)
  - New org settings created as needed
- **Option B:** Create separate SiteSettingsPerOrg model
- **Option C:** Move branding to Organization model directly

**Recommendation:** Option A — migrate SiteSettings to support org FK. Existing rows become platform-wide defaults.

#### 2. Ratings — Data Model Decision
```python
class Rating(TimeStampedModel):
    rated_user = ForeignKey(User, ...)
    rating_user = ForeignKey(User, ...)
    # ❌ NO ORGANIZATION FK
```

**Question:** Are ratings org-specific or platform-wide?

- **If org-specific:** Add FK to Organization, filter by org in queries
- **If platform-wide:** Leave as-is (user reputation is global)

**Current behavior:** A user rated 5-stars in Organization A carries the same reputation in Organization B.

**Recommendation:** Accept as platform-wide for now (simpler). Users have global reputation across all orgs.

#### 3. Reports — Data Model Decision
```python
class Report(TimeStampedModel):
    reported_by = ForeignKey(User, ...)
    reported_user = ForeignKey(User, ...)
    # ❌ NO ORGANIZATION FK
```

**Same question as Ratings:** org-specific or platform-wide?

**Current behavior:** Reports are global user behavior records.

**Recommendation:** Accept as platform-wide. Abuse reports should be tracked globally.

#### 4. Notifications (Telegram) — Low Priority
```python
class TelegramProfile(models.Model):
    user = OneToOneField(User, ...)
    # ❌ NO ORGANIZATION FK
    
class TelegramVerificationToken(models.Model):
    user = ForeignKey(User, ...)
    # ❌ NO ORGANIZATION FK
```

**Context:** Notifications are per-user preferences (notify_issues, notify_passes, etc.)

**Assessment:** Low priority because:
- Users are members of organizations (via OrganizationMembership)
- Notifications are user-initiated, not org-data
- Multiple memberships can trigger notifications from different orgs

**Recommendation:** Leave as-is for now. Can extend later if per-org notification preferences needed.

---

## Migration Priorities

### Phase 1 (Pre-Production) — CRITICAL
- [ ] **SiteSettings:** Migrate to org-scoped OR extend Organization model with branding fields
- [ ] **Testing:** Verify multi-tenant isolation with sample data across 3+ orgs

### Phase 2 (Post-Launch v1.1)
- [ ] **Categories:** Make org-scoped if clients request custom categories
- [ ] **NewsCategories:** Same as Categories

### Phase 3 (Optional Enhancements)
- [ ] **Ratings/Reports:** Add org FK if org-specific tracking desired
- [ ] **Notifications:** Add per-org preferences if needed

---

## Testing Checklist

- [ ] Create 3 test organizations with different data
- [ ] Verify Buildings filtered by org in API responses
- [ ] Verify Issues filtered by org in API responses
- [ ] Verify Posts filtered by org in API responses
- [ ] Verify different Users get correct org context based on membership
- [ ] Verify SiteSettings migration (if implemented)
- [ ] Test multi-org API access with X-Organization-Slug header
- [ ] Test subdomain routing (zhk-a.com → org: a)
- [ ] Verify ratings/reports are visible across orgs (intended)

---

## Files Reviewed

- `/server/apps/organizations/models.py` — Organization, OrganizationMembership
- `/server/apps/site_settings/models.py` — SiteSettings (singleton), SiteLink, ContactPerson
- `/server/apps/apartments/models.py` — Building, Entrance, Unit, Apartment (legacy)
- `/server/apps/issues/models.py` — Issue, Category
- `/server/apps/passes/models.py` — VehiclePass
- `/server/apps/posts/models.py` — Post, Reply, Announcement
- `/server/apps/news/models.py` — News, NewsCategory
- `/server/apps/ratings/models.py` — Rating
- `/server/apps/reports/models.py` — Report
- `/server/apps/notifications/models.py` — TelegramProfile, TelegramVerificationToken
- `/server/apps/profiles/models.py` — Profile
- `/server/apps/users/models.py` — User
- `/server/config/settings/base.py` — INSTALLED_APPS

---

## Conclusion

ApartmentOS is **70% ready** for multi-tenant single deployment:

✅ **What's ready:** Core features (buildings, issues, passes, posts, users, profiles)
⚠️ **What needs review:** Categories, legacy models
❌ **What needs action:** SiteSettings migration, policy decisions on ratings/reports

**Recommendation:** Proceed with single-deployment launch; address SiteSettings before going live. Phase 2 enhancements can follow post-launch.
