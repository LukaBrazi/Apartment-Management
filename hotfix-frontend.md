# 🚨 HOTFIX — Frontend Developer

> **Від:** PM Agent
> **Дата:** 2026-03-21
> **Пріоритет:** 🔴 КРИТИЧНО — реліз заблокований
> **Звіт:** `qa-test-report.md`

---

Після QA-тестування впало **29 тестів з 99**. Тебе стосуються **17 багів** на фронтенді.

Зафіксуй, виправ, запусти тести — і повідом PM.

---

## 🔴 КРИТИЧНО (фіксити сьогодні)

### BUG-001/002/003 — Admin CRUD: після створення елемент не з'являється у списку

**Тести:**
- `tests/functional/admin-create-building.spec.ts:15`
- `tests/functional/admin-create-resident.spec.ts:17`
- `tests/functional/admin-create-worker.spec.ts:18`

**Що не так:** Адмін заповнює форму, сабмітить — але будівля / мешканець / робітник не відображається у таблиці.

**Де дивитись:**
- Компоненти форм: `AdminCreateBuilding`, `AdminCreateResident`, `AdminCreateWorker`
- Після успішного `POST` — чи робиться рефетч списку? (`invalidateTags`, `refetch()`, або `router.refresh()`)
- Чи змінився `data-testid` на елементах списку? Playwright шукає по `data-testid` або тексту.
- Перевір Network tab: чи повертає бекенд `201` після створення?

**Швидкий debug:**
```bash
npx playwright test tests/functional/admin-create-building.spec.ts --headed --slowMo=500
```

---

### BUG-005 — Мешканець створює заявку, але вона не з'являється в адмін-панелі

**Тест:** `tests/functional/issue-admin-flow.spec.ts:12`

**Де дивитись:** Компонент форми створення заявки → після сабміту чи інвалідується кеш адмін-панелі?

---

## 🟠 HIGH (цього тижня)

### BUG-010 — Guard не може закрити пропуск

**Тест:** `tests/functional/guard-close-pass.spec.ts:9`

**Що не так:** Після натискання "Закрити пропуск" статус не оновлюється до `closed`.

**Де дивитись:** Guard portal component → кнопка close pass → `PATCH /api/passes/{id}/` → оновлення UI після відповіді.

---

### BUG-011 — Staff не може створити оголошення / воно не відображається

**Тест:** `tests/functional/announcement-flow.spec.ts:10`

**Де дивитись:** Компонент створення Announcement → перевір `data-testid` на елементах списку.

---

### BUG-012 — Мешканець створює пост — не відображається, API недоступний

**Тести:**
- `tests/functional/post-flow.spec.ts:11` — пост не видно на welcome page
- `tests/functional/post-flow.spec.ts:33` — пост недоступний через API

**Де дивитись:** Post creation form → welcome page rendering → чи передається правильний `Authorization` header при API-запиті?

---

### BUG-013 — Guard flow: assign-issue не відображається у вкладці

**Тест:** `tests/functional/assign-issue-flow.spec.ts:10`

**Що не так:** Адмін призначає заявку → guard не бачить її у `assigned-issues` tab.

**Де дивитись:** Guard portal → tabs component → assigned-issues tab → API query `/api/issues/?assigned_to=me`

---

### BUG-014–018 — Валідаційні помилки не показуються або не українською

**Тести:**
- `issue-validation.spec.ts:17, :50, :70`
- `pass-validation.spec.ts:17, :35`
- `post-validation.spec.ts:17, :35, :66`
- `admin-resident-validation.spec.ts:47`
- `admin-worker-validation.spec.ts:46, :118`

**Що не так:** Форми не показують помилки при некоректному вводі, або показують їх англійською.

**Де дивитись:**

1. **Zod schemas** — чи задані `message` по-українськи?
```ts
// Приклад правильно:
z.string().min(5, { message: "Заголовок занадто короткий" })
z.string().email({ message: "Невірний формат email" })
```

2. **react-hook-form** — чи відображаються `errors.fieldName.message` у JSX?
```tsx
{errors.title && <p className="text-red-500">{errors.title.message}</p>}
```

3. **Toast notifications** — чи обробляється `error.response.data` і виводиться через `toast.error()`?

4. **Перевір усі форми:** `IssueForm`, `PassForm`, `PostForm`, `AdminResidentForm`, `AdminWorkerForm`

---

## 🟡 MEDIUM (наступний спринт, але перевір зараз)

### BUG-019 — `/profile?tab=my-issues` не активує таб

**Тести:**
- `tests/functional/regression-bugs.spec.ts:96`
- `tests/functional/regression-bugs.spec.ts:118`

**Що не так:** Перехід на `/profile?tab=my-issues` не показує вміст табу "Мої заявки".

**Де дивитись:** `app/profile/page.tsx` або Profile компонент:
```ts
// Перевір чи читається searchParams:
const searchParams = useSearchParams()
const tab = searchParams.get('tab') // має повертати 'my-issues'
```

Також перевір navbar — чи посилання веде на `/profile?tab=my-issues`?

---

## ✅ Чеклист після фіксу

- [ ] Admin CRUD — після створення список оновлюється (рефетч / invalidate)
- [ ] Issues flow — заявки видно в адмін-панелі після створення
- [ ] Guard close pass — статус оновлюється в UI
- [ ] Announcement + Post flow — з'являються у списках
- [ ] Всі форми показують українські помилки
- [ ] `/profile?tab=my-issues` — таб активується
- [ ] Запущено Playwright тести локально:
  ```bash
  cd client && npx playwright test --headed
  ```
- [ ] Результати передано PM (оновив цей файл або написав у чат)

---

*🤖 PM Agent | Skandi Apartments | 2026-03-21*
