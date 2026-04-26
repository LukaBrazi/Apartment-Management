# Security Backlog

> Living document for security findings that are known but not yet
> remediated. Each entry should have a CVE / advisory ID, an impact
> assessment, and a target date or "won't fix" justification.

## Why this file exists

PR-8 wired up `pip-audit` and `npm audit` into CI as a `security-scan`
job (`.github/workflows/ci.yml`). The job currently runs with
`continue-on-error: true` so it surfaces findings without blocking
merges. Once we triage the first batch of findings, the goal is:

1. Fix or pin every actionable advisory.
2. Document any "accepted risk" entries in this file with a clear
   justification.
3. Flip the CI job to `continue-on-error: false`, turning regressions
   into hard merge blockers.

## Triage status

The first run of `security-scan` against `main` has not yet been
processed. After it runs, copy the output into the sections below.

### Backend (`pip-audit -r server/requirements/production.txt`)

_(empty — populate after first CI run)_

| Package | Version | CVE / GHSA | Severity | Notes / Action | Owner | ETA |
|---|---|---|---|---|---|---|
| _none yet_ | | | | | | |

### Frontend (`npm audit --audit-level=high --omit=dev`)

_(empty — populate after first CI run)_

| Package | Version | Advisory | Severity | Notes / Action | Owner | ETA |
|---|---|---|---|---|---|---|
| _none yet_ | | | | | | |

## Entry template

```
| left-pad | 1.3.0 | GHSA-xxxx-xxxx | high | Used only by tooling, no runtime exposure — pinned upstream patch landing in v1.3.1 | Dmytro | 2026-05-01 |
```

## Process

- New finding → add row above with `pending` status.
- Fix shipped → remove the row + reference the PR in the commit message.
- Won't fix → keep the row with status `accepted` and a justification.

## Related

- `.github/workflows/ci.yml` → `security-scan` job
- `readme.md` → "Security Headers (PR-8)" section
- `docs/RAILWAY_SETUP.md` → "Production Logs — JSON (PR-8)" section
