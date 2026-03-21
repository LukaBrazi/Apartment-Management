# 🤝 Contributing — Skandi Apartments

## 🧪 TDD — Test-Driven Development

**У цьому проєкті діє принцип TDD. Це не побажання — це вимога.**

> Спочатку тест — потім код. Без тесту — без merge.

---

### Як це працює

```
1. Пишеш тест (RED)     — тест падає, бо функціонал ще не існує
2. Пишеш мінімум коду (GREEN) — тест проходить
3. Рефакторинг (REFACTOR) — чистиш код, тести все ще зелені
```

---

### Backend (Django / pytest)

Тести живуть у `server/apps/tests/`. Запуск:

```bash
make test          # всі тести
make test-cov      # з покриттям коду
```

**Правила:**
- Кожен новий endpoint → мінімум 1 happy path + 1 negative тест
- Permissions обов'язково покриваються (401 / 403 сценарії)
- Валідація серіалізаторів — окремий тест-кейс
- Використовуй `factory_boy` для фікстур — не хардкодь дані

```python
# ✅ Правильно — спочатку тест
def test_non_staff_cannot_create_building(api_client, tenant_user):
    api_client.force_authenticate(tenant_user)
    response = api_client.post("/api/v1/apartments/buildings/create/", {...})
    assert response.status_code == 403

# ❌ Неправильно — код без тесту
class BuildingCreateAPIView(generics.CreateAPIView):
    ...
```

---

### Frontend (Playwright E2E)

Тести живуть у `../sckandi-e2e/tests/`. Запуск:

```bash
make e2e           # проти CI-стеку
make e2e-full      # підняти стек + seed + тести + прибрати
make e2e-ui        # з UI для дебагу
```

**Правила:**
- Кожна нова сторінка або flow → `tests/functional/` spec файл
- Кожна форма → `tests/negative/` validation spec
- Тести пишуться **до** реалізації UI компоненту
- `data-testid` атрибути обов'язкові на інтерактивних елементах

```typescript
// ✅ Правильно — тест до компоненту
test('resident creates issue → appears in admin panel', async ({ page }) => {
  // ...
});

// ❌ Неправильно — компонент без тесту → одразу в main
```

---

### Definition of Done для будь-якої задачі

- [ ] Тести написані **до або разом** з кодом
- [ ] `make test` — всі backend тести green
- [ ] `make e2e` — всі E2E тести green (або нові покривають зміни)
- [ ] Pass rate ≥ 90% перед merge
- [ ] Немає відкритих Critical/Blocker тестів

---

### Чому TDD?

Ми вже бачили що буває без нього — 29 падаючих тестів, security діри (403/401 не повертались), форми без валідації. TDD не сповільнює розробку — він усуває зворотні виправлення.

---

### Гілки і PR

```
main          ← продакшн, захищена
feature/xxx   ← нова фіча (від main)
fix/xxx       ← хотфікс
```

PR в `main` без зелених тестів — не merge.

---

*Питання? Пишіть PM або залишайте коментар у PR.*
