# ApartmentOS SuperAdmin Quick Start Guide

**Target Audience:** Platform administrators managing multiple client organizations  
**Last Updated:** April 2026

---

## What You Need to Know

You're running **ONE** ApartmentOS instance that serves **MANY clients** (Organizations).

- **Old way:** Every client gets their own Railway deploy and database ❌
- **New way:** One Railway, one database, multiple Organizations ✅

---

## 5-Minute Setup for a New Client

### Step 1: Create Organization in Django Admin

1. Go to `https://api.apartmentos.com/django-admin/`
2. **Organizations → Organizations → Add Organization**
3. Fill in:
   - **Name:** ЖК Сонячний
   - **Slug:** zhk-sunny (auto-generated, but customize if needed)
   - **Type:** housing_complex
   - **City:** Київ
   - **Address:** вул. Тестова, 1
   - **Email:** admin@zhk-sunny.com
   - **Phone:** +380671234567
4. Click **Save**

**That's it!** Organization is created.

---

### Step 2: Add Director User

1. **Organizations → Organization Memberships → Add Membership**
2. Fill in:
   - **User:** (click **+** to create new user, or select existing)
   - **Organization:** ЖК Сонячний
   - **Role:** director
   - **Is Active:** ☑ (checked)
3. Click **Save**

**What happens:** Director gets email invitation with login link.

---

### Step 3: Add DNS CNAME (Cloudflare)

1. Go to **Cloudflare Dashboard → example.com → DNS**
2. Add CNAME record:
   ```
   Type: CNAME
   Name: zhk-sunny
   Content: cname.vercel-dns.com
   TTL: Auto
   ```
3. Or if already have wildcard:
   ```
   *.apartmentos.com → cname.vercel-dns.com (one-time setup)
   ```

**Wait 5-15 minutes for DNS to propagate.**

---

### Step 4: Test

Director can now login at:
```
https://zhk-sunny.apartmentos.com
```

API access:
```bash
curl -H "X-Organization-Slug: zhk-sunny" https://api.apartmentos.com/api/v1/orgs/organizations/self/
# Should return organization details
```

---

## Common Tasks

### How to: Add More Staff to Client's Organization

1. **Django Admin → Organizations → Memberships**
2. **Add Membership:**
   - **User:** (existing or create new)
   - **Organization:** (select client)
   - **Role:** admin / staff / resident
   - **Is Active:** ☑

Staff member gets email invitation.

---

### How to: Customize Client's Branding

1. **Django Admin → Site Settings → Site Settings**

⚠️ **IMPORTANT:** SiteSettings is currently singleton (pk=1). All clients see the same branding.

**Options:**
- Update SiteSettings for all clients
- Or customize per-client after SiteSettings migration:
  - **Platform Name:** (shows in all clients)
  - **Primary Color:** (all clients use this)
  - **Logo URL:** (all clients use this)

**Workaround for now:**
- Request each client provides branding preferences
- Note them somewhere
- After SiteSettings migration, apply individually

---

### How to: View Organization Data

1. **Django Admin → Organizations → Organizations**
2. Click on organization name
3. See:
   - **Buildings** created by this org
   - **Issues** reported by this org
   - **Posts** published by this org
   - **Memberships** (users in org)
   - etc.

---

### How to: API Management (Advanced)

Create/manage organizations via API:

```bash
# Create organization
curl -X POST https://api.apartmentos.com/api/v1/orgs/organizations/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "ЖК Новий",
    "slug": "zhk-new",
    "type": "housing_complex",
    "city": "Київ"
  }'

# Get all organizations
curl -H "Authorization: Bearer $TOKEN" \
  https://api.apartmentos.com/api/v1/orgs/organizations/

# Get specific organization
curl -H "Authorization: Bearer $TOKEN" \
  https://api.apartmentos.com/api/v1/orgs/organizations/zhk-sunny/
```

---

## How Organization Detection Works

### For Website (Frontend)

When user visits `zhk-sunny.apartmentos.com`:

1. Vercel (Next.js) sees subdomain
2. Extracts slug: `zhk-sunny`
3. Stores in context/cookies
4. Frontend makes API requests with header: `X-Organization-Slug: zhk-sunny`
5. Backend filters data for that org

**Result:** User sees only zhk-sunny's data (buildings, issues, posts, etc.)

### For API

When external system calls API:

```bash
# Request with org header
curl -H "X-Organization-Slug: zhk-sunny" \
  https://api.apartmentos.com/api/v1/issues/

# Backend automatically filters:
# SELECT * FROM issues WHERE organization_id = (SELECT id FROM organizations WHERE slug = 'zhk-sunny')
```

---

## Troubleshooting

### Issue: DNS not resolving

1. Check Cloudflare DNS is set:
   ```bash
   dig zhk-sunny.apartmentos.com
   ```
   Should show CNAME pointing to Vercel

2. Wait 24-48 hours for full propagation

3. Check status: `https://dnschecker.org/`

### Issue: Frontend loads but API 403 (Forbidden)

- Check `X-Organization-Slug` header is set correctly
- Verify organization exists: `django-admin → Organizations`
- Check user has membership in that org

### Issue: Staff member can't see organization data

1. Verify membership is created: `Django Admin → Memberships`
2. Verify **Is Active** is ☑ (checked)
3. Verify **Role** is not RESIDENT (residents see limited data)
4. Ask user to clear browser cache and re-login

### Issue: Director can't invite staff

- Check Director role has permission: Director + Admin can invite
- If STAFF role, they can't invite (by design)

---

## Before Going Live

**Checklist:**

- [ ] Create test organizations (A, B, C)
- [ ] Add directors to each
- [ ] Add buildings/issues to each
- [ ] Verify data isolation (A's issues invisible to B)
- [ ] Test multi-org API calls
- [ ] Test DNS resolution for all domains
- [ ] Set up CORS properly: `CORS_ALLOWED_ORIGINS=https://*.apartmentos.com`
- [ ] Enable HTTPS everywhere
- [ ] Set up monitoring/alerting
- [ ] Test database backups
- [ ] Document client onboarding process for your team

---

## Important Concepts

### Organization = Client

One Organization = One Client (ЖК, Management Company, etc.)

### Slug = Organization ID

Every organization has a unique **slug** (e.g., `zhk-sunny`).

- Used in domain: `zhk-sunny.apartmentos.com`
- Used in API header: `X-Organization-Slug: zhk-sunny`
- Must be URL-safe (lowercase, hyphens, no spaces)

### User ≠ Organization

Users are global. One person can be:
- Director in Organization A
- Staff in Organization B
- Resident in Organization C

**Membership** table tracks relationship:
```
User: ivan@example.com
└─ Organization A (role: director)
└─ Organization B (role: staff)
└─ Organization C (role: resident)
```

### Data Isolation

Every model with `organization` FK is scoped:

✅ **Scoped models** (filtered by org):
- Buildings
- Issues
- Passes
- Posts
- News

❌ **Global models** (not org-filtered):
- Users (global, but see org context)
- Ratings (user reputation is global)
- Reports (user reports are global)

---

## Database Snapshots

To create a snapshot for a specific organization:

```bash
# Connect to Railway PostgreSQL
railway connect postgresql

# Export organization data
psql -c "
  SELECT * FROM apartments_building WHERE organization_id = 1;
  SELECT * FROM issues_issue WHERE organization_id = 1;
  SELECT * FROM issues_issue_updates WHERE issue_id IN (
    SELECT id FROM issues_issue WHERE organization_id = 1
  );
" > org_data.sql
```

---

## Useful Django Admin URLs

```
/django-admin/                          # Home
/django-admin/organizations/            # Organizations list
/django-admin/organizations/add/        # Add organization
/django-admin/organizations/memberships/ # User memberships
/django-admin/apartments/building/       # Buildings
/django-admin/issues/issue/              # Issues
/django-admin/posts/post/                # Posts
/django-admin/news/news/                 # News
/django-admin/site_settings/sitesettings/  # Settings (singleton)
```

---

## Support & Escalation

**If you encounter issues:**

1. Check **Rails Logs:** `railway logs --service django-server`
2. Check **Vercel Logs:** `vercel logs --prod`
3. Check **Database:** Connect and verify org data exists
4. Contact development team with:
   - Organization slug
   - Exact error message
   - Time of occurrence
   - Steps to reproduce

---

## Next Steps

1. ✅ Understand single-deployment model
2. ✅ Practice adding test organizations
3. ✅ Test end-to-end (organization → DNS → frontend → API)
4. ✅ Document your client onboarding process
5. ✅ Start adding real clients!

**Questions?** Check `DEPLOYMENT_GUIDE.md` for detailed architecture info.
