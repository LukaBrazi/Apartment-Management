# Kubernetes manifests

> **Status:** reference only. The platform currently runs on Railway;
> the nightly demo reset is wired via **Celery Beat**, not these
> manifests. See `server/apps/common/tasks.py::seed_demo_reset` and the
> `seed-demo-reset-nightly` entry in
> `server/config/settings/base.py::CELERY_BEAT_SCHEDULE`.
>
> Keep this folder as the migration target if/when we move off Railway
> onto a Kubernetes cluster — the Celery task can be deleted in favour
> of the CronJob below at that point.

Infrastructure manifests for ApartmentOS. Not consumed by `docker-compose`
or Railway — these target a future Kubernetes staging/production cluster.

## Files

- `demo-reset-cronjob.yaml` — nightly 23:00 Europe/Kyiv CronJob that runs
  `manage.py seed_demo --reset --passwords-from-env` and a matching
  `ServiceAccount`. See [`DEMO_SEED_PLAN.md`](../../../client/docs/DEMO_SEED_PLAN.md)
  §10 for the reasoning.

## First-time setup

```bash
# Namespace
kubectl create namespace apartmentos

# Demo password secret (DO NOT commit the value)
kubectl -n apartmentos create secret generic demo-seed-secrets \
  --from-literal=DEMO_PASSWORD='<strong-demo-password>'

# DB connection secret (shared with the web Deployment)
kubectl -n apartmentos create secret generic apartmentos-db \
  --from-literal=DATABASE_URL='postgres://...'

# Apply the CronJob + ServiceAccount
kubectl apply -f demo-reset-cronjob.yaml
```

## Verify

```bash
kubectl -n apartmentos get cronjob demo-reset-nightly
kubectl -n apartmentos get jobs --selector=app.kubernetes.io/component=demo-reset
kubectl -n apartmentos logs -l app.kubernetes.io/component=demo-reset --tail=200
```

## Manual trigger (kill-switch)

```bash
# One-off reset right now, without waiting for 23:00:
kubectl -n apartmentos create job --from=cronjob/demo-reset-nightly \
  demo-reset-manual-$(date +%s)
```

## Rollback

```bash
kubectl -n apartmentos delete -f demo-reset-cronjob.yaml
```
