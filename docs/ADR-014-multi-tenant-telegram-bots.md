# ADR-014 — Multi-tenant Telegram bots

- Status: **Accepted**
- Date: 2026-04-20
- Deciders: CEO (Dmytro)
- Supersedes: single global `TELEGRAM_BOT_TOKEN` (ADR-untitled, introduced when
  ApartmentOS was single-tenant).

## Context

Today the platform has exactly **one** Telegram bot. Its token (`TELEGRAM_BOT_TOKEN`)
and username (`TELEGRAM_BOT_USERNAME`) live in Django settings, i.e. in environment
variables for the whole app. Every notification (issue update, new issue, pass
approval, announcement) goes through that single bot.

This blocks three things:

1. **White-label.** Each housing complex wants its own brand end-to-end, including
   the Telegram bot residents connect to: "ОСББ Зелений Квартал" → `@ZelenyiKvartalBot`,
   "ОСББ Перлина" → `@PerlynaOSBBBot`. One shared bot breaks the white-label promise.
2. **Data isolation.** One token = one owner of every chat. If it were ever compromised,
   an attacker could DM every resident of every ЖК the platform serves.
3. **Org-local control.** Right now only the platform operator can rotate the token or
   disable the bot. Each organization should be able to wire up (and revoke) its own
   bot independently, without the platform needing to ship a deploy.

## Decision

We introduce a new model, `OrganizationBot`, that stores per-organization Telegram
bot credentials. Every notification path resolves which bot to use from the
organization the notification belongs to. There is **no** platform-wide fallback —
if an org has not configured a bot, no Telegram messages are sent for that org.

### 1. Feature flag gating

Multi-tenant Telegram is a **pluggable feature** per organization. It is controlled
by the existing `Organization.features` JSONField, key `telegram_notifications`:

```python
org.is_feature_enabled("telegram_notifications")  # True ⇒ feature on
```

If the flag is off, all notification tasks short-circuit to a no-op regardless of
whether an `OrganizationBot` row exists. This gives the platform operator a
kill-switch per-org without touching bot records.

### 2. Storage model

```
OrganizationBot
├── organization        FK → Organization  (related_name="telegram_bots")
├── bot_username        str                (e.g. "ZelenyiKvartalBot", no @)
├── encrypted_token     TextField          (Fernet ciphertext of bot token)
├── webhook_secret      str(64)            (autogen; Telegram→us HMAC check)
├── internal_secret     str(64)            (autogen; bot→our API legacy path)
├── is_active           bool               (per-org kill-switch)
├── is_primary          bool               (future: primary + backup bots)
├── created_by          FK → User          (audit, SET_NULL on delete)
├── last_tested_at      datetime?          (set by "Test bot" admin action)
├── last_test_ok        bool?              (last test result)
├── last_test_error     text               (failure message for debugging)
└── created_at, updated_at

Partial unique: (organization) where is_primary=True
```

`is_primary` + partial-unique constraint lets us later add a failover bot per org
without schema changes. For the MVP we only ever create primary rows.

### 3. Token encryption

Bot tokens are the keys to the kingdom — leakage means full chat access to every
resident of that org. We encrypt them at rest with Fernet (AES-128-CBC + HMAC):

- Encryption key: `TELEGRAM_BOT_ENCRYPTION_KEY` env var, 32 base64 bytes.
  Generated once per environment with `Fernet.generate_key()`.
- Accessors: `OrganizationBot.bot_token` is a `@property` that decrypts on read,
  `@bot_token.setter` encrypts on write. The raw ciphertext stays in
  `encrypted_token` TextField.
- The API never returns the raw token. Serializers expose `token_masked`
  (first 4 chars + `…` + last 4 chars) and `is_configured: bool`. Admin UI
  shows the same masked representation and accepts a new token only on write.

We use `cryptography.fernet.Fernet` (already an indirect dep) directly instead
of adding `django-cryptography` because the surface is tiny and
django-cryptography has known compat issues with Django 4.2+.

### 4. TelegramProfile rescoping

The current `TelegramProfile(user OneToOne, chat_id unique)` is globally scoped
and can't represent the same user on two different bots. Rescope to per-org:

- Add `organization` FK (CASCADE).
- Drop `OneToOneField`; make `user` a `ForeignKey` and add
  `unique_together = ("user", "organization")`.
- Drop global uniqueness on `chat_id`; add per-org uniqueness
  `unique_together = ("organization", "chat_id")` — the same Telegram user DMing
  two bots naturally gets two distinct `chat_id`s (one per bot), so a global
  unique would be wrong.
- Data migration: existing profiles get attributed to the user's primary
  `OrganizationMembership.organization`. Users with no membership get their
  profile deactivated (`is_active=False`) rather than deleted — preserves audit.

`TelegramVerificationToken` gains an `organization` FK so one user can connect
to different orgs' bots independently. Generating a token requires an explicit
`organization_id` in the request.

### 5. Delivery: webhook in prod, polling in dev

Running N polling processes (one per bot) in production doesn't scale and
doubles our footprint per new tenant. We go hybrid:

- **Production (`settings.ENVIRONMENT == "production"`):** webhook mode.
  Each bot's webhook URL is
  `https://apartmentos.org/api/v1/notifications/telegram/webhook/<org-slug>/`.
  Telegram signs updates with `webhook_secret` via the
  `X-Telegram-Bot-Api-Secret-Token` header; we validate it in the view.
  A new management command `setup_telegram_webhooks` registers webhooks with
  Telegram for every `is_active` `OrganizationBot`, idempotent.
- **Dev (everything else):** polling mode, one process per org bot, started
  with `python manage.py run_bot --org-slug=<slug>`. No ngrok needed.

The webhook view and the polling handler share the same dispatcher code —
both normalize `Update`s into `handle_command(org, chat_id, command, args)`.

### 6. Permissions: super_admin only

- Django admin: only users with `is_superuser=True` OR
  `OrganizationMembership.role == super_admin` can view/edit `OrganizationBot`.
  Director and Admin do **not** get access. (Decision per CEO 2026-04-20.)
- Frontend `/admin/telegram-bot/` route: guarded by `useAuthNavigation` + a
  `requireRole("super_admin")` check. Directors see a 403.
- API: `IsSuperAdmin` custom permission on all CRUD endpoints.

### 7. Fallback policy

Silent. An organization without an `is_active=True` `OrganizationBot`, OR with
`features.telegram_notifications` off, receives zero Telegram messages. The
platform logs it at `INFO` once per task (not per call) and moves on. No
fallback to a shared bot.

This prevents the scenario where one compromised platform bot sees the chats
of every org that "forgot" to configure their own.

### 8. Onboarding flow

Super-admin workflow (documented in `docs/TELEGRAM_BOT_SETUP.md`):

1. In Telegram, DM `@BotFather`, `/newbot`, pick a name and username.
2. Copy the token BotFather returns.
3. In `/admin/telegram-bot/` on the ApartmentOS site, pick the org, paste
   token + username, click **Save**. Backend generates `webhook_secret`
   and `internal_secret`.
4. Click **Test bot** — backend calls `getMe` with the token. Green badge
   confirms the creds are good.
5. In production, the UI shows the webhook URL. Admin copies it into
   BotFather's `/setwebhook` or the backend's `setup_telegram_webhooks`
   command does it for them.
6. Activate feature flag: `org.features["telegram_notifications"] = True`.
   Residents now see the "Connect Telegram" button in the app.

## Consequences

### Good

- Clean white-label per ЖК.
- Strict data isolation: a leaked token affects one tenant, not all.
- Per-org kill-switch without a platform deploy.
- Future-ready for failover bot (partial-unique already allows it).
- Silent fallback = zero config-drift surprises for new orgs.

### Bad / trade-offs

- More moving parts: N bots = N webhooks to register and renew.
- A new secret to manage: `TELEGRAM_BOT_ENCRYPTION_KEY`. Key loss = all tokens
  go unreadable and have to be re-entered by super_admin. We document rotation
  in the deploy runbook.
- Existing `TelegramProfile` rows need a data migration to attribute them
  to an org. Rows without a clear org are deactivated (not deleted).
- Super_admin has to manually generate each bot via BotFather — we can't
  automate bot creation (BotFather is interactive-only). Acceptable price
  for the isolation guarantee.

### Deprecated

- `TELEGRAM_BOT_TOKEN` env var becomes unused after migration completes.
  We keep it readable in settings for one release cycle, log a warning if
  set, then drop it.
- `TELEGRAM_BOT_USERNAME` env var: same deprecation.

## Rollout

1. **Phase 1** — model + migration + encryption + ADR merged.
2. **Phase 2** — rescope `TelegramProfile` with data migration.
3. **Phase 3** — refactor `utils.py` + Celery tasks to resolve bot per-org.
4. **Phase 4** — webhook endpoint + polling update + setup command.
5. **Phase 5** — Django admin for super_admin.
6. **Phase 6** — Next.js `/admin/telegram-bot/` UI.
7. **Phase 7** — tests covering model, tasks, webhook, admin permissions.
8. **Phase 8** — docs, reset-scope integration, demo seed (inactive placeholder).

All phases land on the single branch `feat/multi-tenant-telegram` per CEO
request (consolidate to reduce branch sprawl).

## Alternatives considered

- **Shared bot with per-org channels.** Cheaper but breaks white-label and
  doesn't give tenants control. Rejected.
- **`django-cryptography` for encrypted fields.** Extra dep, compat issues
  with Django 4.2+. Rolled our own thin Fernet wrapper instead.
- **Keep platform-default fallback.** Rejected: first compromise = every
  unconfigured org's residents exposed.
- **One polling process per org.** Doesn't scale beyond a handful of orgs.
  Kept only for dev.
