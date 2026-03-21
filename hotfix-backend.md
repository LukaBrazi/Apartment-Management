# 🚨 HOTFIX — Backend Developer

> **Від:** PM Agent
> **Дата:** 2026-03-21
> **Пріоритет:** 🔴 КРИТИЧНО — реліз заблокований
> **Звіт:** `qa-test-report.md`

---

Після QA-тестування впало **29 тестів з 99**. Тебе стосуються **12 критичних багів** на бекенді.

Зафіксуй, виправ, запусти тести — і повідом PM.

---

## 🔴 КРИТИЧНО (фіксити сьогодні)

### BUG-006 — Non-staff може створювати будівлі (403 не повертається)
**Тест:** `tests/negative/admin-building-validation.spec.ts:80`
**Що не так:** API приймає запит на створення будівлі від звичайного юзера замість 403.
**Де дивитись:** `server/apps/buildings/views.py` → `BuildingViewSet`
**Перевір:** `permission_classes = [IsAuthenticated, IsAdminUser]` або кастомний `IsStaff`

---

### BUG-007 — Non-staff може створювати workers (403 не повертається)
**Тест:** `tests/negative/admin-worker-validation.spec.ts:138`
**Що не так:** Аналогічно — API не захищений.
**Де дивитись:** `server/apps/users/views.py` → `WorkerViewSet`
**Перевір:** `permission_classes`

---

### BUG-008a — API приймає пропуск з минулою датою (має повертати 400)
**Тест:** `tests/negative/pass-validation.spec.ts:74`
**Що не так:** `POST /api/passes/` з `date` у минулому — API повертає 200 або 201 замість 400.
**Де дивитись:** `server/apps/passes/serializers.py`
**Перевір:** валідатор поля `date` — `validate_date()` або `validate()` → `raise serializers.ValidationError`

---

### BUG-008b — Неавторизований юзер може створити пропуск (401 не повертається)
**Тест:** `tests/negative/pass-validation.spec.ts:99`
**Що не так:** `POST /api/passes/` без токена — API не повертає 401.
**Де дивитись:** `server/apps/passes/views.py` → `VehiclePassViewSet`
**Перевір:** `permission_classes = [IsAuthenticated]`

---

### BUG-009 — Неавторизований юзер може створити пост (401 не повертається)
**Тест:** `tests/negative/post-validation.spec.ts:85`
**Що не так:** `POST /api/posts/` без токена — не повертає 401.
**Де дивитись:** `server/apps/posts/views.py`
**Перевір:** `permission_classes = [IsAuthenticated]`

---

### BUG-004 — Issues flow повністю зламаний
**Тести:**
- `tests/functional/admin-issue-status.spec.ts:13` — адмін не може змінити статус
- `tests/functional/admin-issue-status.spec.ts:73` — API повертає некоректний статус
- `tests/functional/issue-admin-flow.spec.ts:12` — мешканець створює заявку, але вона не з'являється в адмін-панелі

**Де дивитись:** `server/apps/issues/views.py`, `serializers.py`, `models.py`
**Перевір:**
- Чи є endpoint `PATCH /api/issues/{id}/` з полем `status`?
- Чи правильні `permission_classes` для адміна?
- Чи немає свіжого коміту що зламав `transition_to()` або серіалізатор?

```bash
git log --oneline -10 -- server/apps/issues/
```

---

## 🟠 HIGH (цього тижня)

### BUG-014/015/016/017/018 — Українські повідомлення про помилки не приходять від API

**Тести:** `admin-resident-validation:47`, `admin-worker-validation:46 & :118`, `issue-validation:70`, `pass-validation:35`

**Що не так:** Серіалізатори повертають помилки англійською або взагалі не повертають detail українською.

**Перевір:**
- `server/apps/*/serializers.py` → `raise serializers.ValidationError("Текст українською")`
- `server/settings/base.py` → `LANGUAGE_CODE = 'uk'`
- Дублікат email у Worker — чи є кастомний `UniqueValidator` з українським меседжем?

---

## ✅ Чеклист після фіксу

- [ ] Виправлено `permission_classes` у Buildings, Workers, Passes, Posts ViewSets
- [ ] Виправлено валідацію дати у PassSerializer
- [ ] Розслідувано і виправлено Issues flow
- [ ] Перевірено Ukrainian error messages у серіалізаторах
- [ ] Запущено pytest локально — всі backend тести green:
  ```bash
  cd server && pytest -v
  ```
- [ ] Запущено Playwright тести локально або на dev:
  ```bash
  cd client && npx playwright test tests/negative/ tests/functional/admin-issue-status.spec.ts
  ```
- [ ] Результати передано PM (оновив цей файл або написав у чат)

---

*🤖 PM Agent | Skandi Apartments | 2026-03-21*
