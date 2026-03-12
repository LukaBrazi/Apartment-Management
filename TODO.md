# TODO — Alpha Apartments (ОСББ/Керуюча в кишені)

## Готово (MVP v1)

- [x] Модель Building → Entrance → Unit (ієрархія нерухомості)
- [x] Міграція даних з Apartment у Unit (backward-compat)
- [x] Категорії заявок із SLA (`sla_hours`, `due_at`, `is_overdue`)
- [x] Розширений потік статусів: `reported → accepted → in_progress → done | rejected`
- [x] Метод `transition_to()` з валідацією переходів
- [x] Email-сповіщення при вирішенні заявки
- [x] Оголошення (Announcement), прив'язані до будинку
- [x] Команда `seed_demo` (демо-дані, ідемпотентна)
- [x] Pytest + factory_boy (72 тести)
- [x] Docker Compose локальне середовище (PostgreSQL, Redis, MinIO, Mailpit, Nginx)
- [x] Кастомна адмін-панель (мешканці, робітники, будинки, заявки, перепустки, пости)
- [x] Портал охорони + перепустки для авто
- [x] README українською + Makefile
- [x] BSL-1.1 ліцензія

---

## Черга фіч — детальні промти для розробки

> Кожен блок нижче — готовий промт. Копіюй і запускай розробку.

---

### 🔔 ФІЧА 1 — Telegram-нотифікації

**Статус:** `[ ] не розпочато`

**Промт для розробки:**

```
Додай Telegram-нотифікації до проєкту Django Apartment Management.

Стек: Django 4.2, Celery 5, Redis, python-telegram-bot або httpx (прямий Bot API).

=== БЕКЕНД ===

1. Нова Django-app `server/apps/notifications/`:
   - Модель `TelegramProfile`:
     - OneToOne → Profile
     - `chat_id` CharField(unique=True, null=True)
     - `is_verified` BooleanField(default=False)
     - `verification_code` CharField(max_length=6, null=True) — одноразовий код
   - Celery task `send_telegram_message(chat_id: str, text: str)` — надсилає повідомлення через Bot API (httpx POST до api.telegram.org/bot{TOKEN}/sendMessage)
   - Утиліта `notify_user(profile_id, text)` — знаходить TelegramProfile, якщо is_verified=True — ставить задачу в чергу

2. Webhook Django View (або polling через management command для локального dev):
   - POST /api/v1/telegram/webhook/ — обробляє /start команду від користувача
   - При /start: витягує verification_code з тексту (/start CODE), знаходить TelegramProfile, встановлює chat_id, is_verified=True
   - Відповідає "Ви успішно підключили Telegram-сповіщення!"

3. API для прив'язки:
   - POST /api/v1/telegram/link/ (IsAuthenticated) — генерує 6-значний verification_code, зберігає в TelegramProfile, повертає deep-link: https://t.me/{BOT_USERNAME}?start={CODE}
   - GET /api/v1/telegram/status/ — повертає { linked: bool, chat_id_masked: str }
   - DELETE /api/v1/telegram/unlink/ — скидає chat_id та is_verified

4. Підключи нотифікації до існуючих подій:
   a) `apps/issues/views.py` — при переході статусу заявки (transition_to) через сигнал або явний виклик:
      - Мешканцю: "📋 Ваша заявка #{id} '{title}' змінила статус: {old} → {new}"
      - Якщо статус 'accepted': "✅ Заявку прийнято в роботу"
      - Якщо статус 'done': "🎉 Заявку виконано! Оцініть роботу майстра."
      - Якщо статус 'rejected': "❌ Заявку відхилено."

   b) `apps/passes/views.py` — при закритті перепустки (POST /passes/{id}/close/):
      - Мешканцю-власнику перепустки: "🚗 Авто {car_number} проїхало на територію ЖК о {time}"

5. Налаштування:
   - TELEGRAM_BOT_TOKEN в .envs/.local/.django.env
   - TELEGRAM_BOT_USERNAME в settings
   - Production: зареєструй webhook через POST до api.telegram.org/bot{TOKEN}/setWebhook

6. Тести (server/apps/tests/test_telegram.py):
   - test_link_generates_code — POST /telegram/link/ повертає deep-link
   - test_webhook_verifies_user — симулює /start CODE, перевіряє is_verified=True
   - test_notify_on_issue_transition — при переході статусу Celery task ставиться в чергу (mock)
   - test_notify_on_pass_close — аналогічно для перепустки

=== ФРОНТЕНД ===

Сторінка /profile/edit — додай секцію "Telegram-сповіщення":
- Якщо не підключено: кнопка "Підключити Telegram" → POST /api/v1/telegram/link/ → відкрити deep-link у новій вкладці + показати інструкцію "Натисніть START у чаті з ботом"
- Якщо підключено: зелений бейдж "✅ Telegram підключено" + кнопка "Відключити"
- Polling кожні 3 секунди після натискання "Підключити" для перевірки is_verified (GET /telegram/status/)

Redux: додай `telegramApiSlice` в `client/src/lib/redux/features/telegram/`.

Стиль: відповідно до існуючого дизайну (rounded-xl, dark: підтримка, кольори #3D7A8A).
```

---

### 💰 ФІЧА 2 — Платіжки за комунальні послуги

**Статус:** `[ ] не розпочато`

**Промт для розробки:**

```
Додай модуль комунальних платежів до Django Apartment Management.

=== БЕКЕНД ===

1. Нова app `server/apps/billing/`:

   Моделі:

   a) `UtilityService` — вид послуги:
      - name: CharField (Водопостачання, Електрика, Газ, Опалення, Вивіз сміття, Утримання будинку)
      - unit: CharField (м³, кВт·год, Гкал, грн/міс)
      - is_active: BooleanField(default=True)

   b) `UtilityBill` — платіжка:
      - unit: FK → apartments.Unit
      - service: FK → UtilityService
      - period: DateField (перше число місяця, напр. 2024-12-01)
      - quantity: DecimalField(max_digits=10, decimal_places=3, null=True) — спожита кількість
      - rate: DecimalField(max_digits=10, decimal_places=4) — тариф на момент виставлення
      - amount: DecimalField(max_digits=10, decimal_places=2) — сума = quantity * rate
      - due_date: DateField — термін оплати (зазвичай 25-те число місяця)
      - status: CharField choices=['pending', 'paid', 'overdue', 'cancelled']
      - created_by: FK → User (адмін/диспетчер)
      - created_at, updated_at

   c) `Payment` — факт оплати:
      - bill: FK → UtilityBill (OneToOne або Many, якщо часткова оплата)
      - paid_by: FK → User
      - amount_paid: DecimalField
      - paid_at: DateTimeField(auto_now_add=True)
      - method: CharField choices=['manual', 'online', 'bank_transfer']
      - transaction_id: CharField(null=True) — зовнішній ID транзакції
      - receipt_url: URLField(null=True) — посилання на квитанцію
      - note: TextField(null=True)

   d) `BillBatch` — пакетне виставлення:
      - building: FK → Building
      - period: DateField
      - created_by: FK → User
      - created_at: DateTimeField
      - total_bills: IntegerField
      - status: CharField choices=['draft', 'sent', 'partial', 'closed']

2. Серіалізатори:
   - `UtilityBillSerializer` — read (для мешканця): id, service_name, period_display, amount, status, due_date, is_overdue
   - `UtilityBillCreateSerializer` — write (для адміна): unit, service, period, quantity, rate, due_date
   - `PaymentSerializer` — read
   - `PaymentCreateSerializer` — write: bill_id, amount_paid, method, transaction_id

3. Views та URLs:

   Мешканець:
   - GET /api/v1/billing/my-bills/ — власні платіжки (фільтр: status, period)
   - GET /api/v1/billing/my-bills/{id}/ — деталь
   - POST /api/v1/billing/my-bills/{id}/pay/ — позначити як оплачено (manual)

   Адмін (IsAdminUser):
   - GET /api/v1/billing/bills/ — всі платіжки (фільтр: building, unit, status, period)
   - POST /api/v1/billing/bills/ — створити одну платіжку
   - PATCH /api/v1/billing/bills/{id}/ — змінити статус/суму
   - POST /api/v1/billing/bills/batch/ — пакетне виставлення для будинку:
     Body: { building_id, period, bills: [{service_id, unit_id, quantity, rate}] }
     Створює UtilityBill для кожного юніту, повертає BillBatch
   - GET /api/v1/billing/services/ — список послуг
   - POST /api/v1/billing/services/ — додати послугу

4. Celery tasks:
   - `mark_overdue_bills()` — щодня о 00:01: переводить прострочені pending → overdue
   - `send_bill_reminder(bill_id)` — нагадування мешканцю за 3 дні до due_date (email + Telegram)
   - `send_monthly_bills_summary(building_id, period)` — зведення після пакетного виставлення

5. Django Admin:
   - Інлайн `PaymentInline` в `UtilityBillAdmin`
   - Дія "Виставити платіжки для будинку" (batch create через форму)
   - Фільтри: статус, будинок, місяць

6. Тести (test_billing.py):
   - test_bill_creation — адмін створює платіжку
   - test_batch_creation — пакет для будинку
   - test_tenant_sees_own_bills — мешканець бачить тільки свої
   - test_manual_payment — POST /pay/ змінює статус
   - test_overdue_task — Celery task правильно оновлює статуси

=== ФРОНТЕНД ===

1. Сторінка мешканця /billing:
   - Список платіжок (таблиця або картки): Місяць, Послуга, Сума, Статус, Термін
   - Бейджі статусу: 🟡 Очікує оплати / 🔴 Прострочено / ✅ Оплачено
   - Кнопка "Оплатити" для pending/overdue → підтвердження → POST /pay/
   - Фільтр за місяць та статус
   - Лічильник боргу вгорі (сума всіх pending+overdue)

2. Адмін-сторінка /admin/billing:
   - Вкладки: Платіжки / Пакетне виставлення / Послуги
   - Форма пакетного виставлення: вибір будинку, місяць, завантаження CSV або ручне введення тарифів
   - Таблиця з фільтрами, bulk-action "Позначити оплаченими"

3. Redux: `billingApiSlice` в `client/src/lib/redux/features/billing/`

Стиль: відповідно до існуючого дизайну (#3D7A8A, rounded-xl, dark mode).
```

---

### 💳 ФІЧА 3 — Онлайн-оплата платіжок

**Статус:** `[ ] не розпочато`

**Промт для розробки:**

```
Додай онлайн-оплату комунальних платіжок до Django Apartment Management.
Передумова: ФІЧА 2 (модуль billing) вже реалізована.

Платіжний провайдер: LiqPay (популярний в Україні) або Stripe (для тестування).
Реалізуй обидва через абстрактний інтерфейс з можливістю перемикання.

=== БЕКЕНД ===

1. Абстракція платіжного провайдера (`server/apps/billing/payment_providers/`):

   `base.py`:
   class PaymentProvider(ABC):
       @abstractmethod
       def create_payment_url(self, bill: UtilityBill, return_url: str) -> str: ...
       @abstractmethod
       def verify_callback(self, data: dict) -> PaymentResult: ...

   `liqpay.py` — реалізація LiqPay:
   - Генерує data+signature за LiqPay API v3
   - POST до api.liqpay.ua/api/3/checkout
   - Верифікація callback через SHA1(PRIVATE_KEY + data + PRIVATE_KEY)

   `stripe_provider.py` — реалізація Stripe:
   - stripe.checkout.Session.create(...)
   - Webhook верифікація через stripe.Webhook.construct_event

2. Views:
   - POST /api/v1/billing/bills/{id}/checkout/ (IsAuthenticated, власник юніту):
     - Перевіряє що bill.status == 'pending' або 'overdue'
     - Викликає provider.create_payment_url(bill, return_url)
     - Повертає { checkout_url: "https://..." }

   - POST /api/v1/billing/payments/callback/ (AllowAny — LiqPay надсилає POST):
     - Верифікує підпис
     - Знаходить bill за order_id
     - Якщо успішно: bill.status = 'paid', створює Payment(method='online', transaction_id=...)
     - Тригерить Telegram/Email нотифікацію
     - Повертає 200 OK (LiqPay чекає 200)

   - GET /api/v1/billing/bills/{id}/payment-status/ — статус оплати для polling після redirect

3. Модель Payment розширення (якщо не додано у ФІЧІ 2):
   - provider: CharField choices=['liqpay', 'stripe', 'manual']
   - raw_callback: JSONField(null=True) — зберігати сирий callback для аудиту

4. Налаштування:
   PAYMENT_PROVIDER = 'liqpay'  # або 'stripe'
   LIQPAY_PUBLIC_KEY = env('LIQPAY_PUBLIC_KEY')
   LIQPAY_PRIVATE_KEY = env('LIQPAY_PRIVATE_KEY')
   STRIPE_SECRET_KEY = env('STRIPE_SECRET_KEY', default='')
   STRIPE_WEBHOOK_SECRET = env('STRIPE_WEBHOOK_SECRET', default='')

5. Тести (test_payments.py):
   - test_checkout_url_generated — POST /checkout/ повертає URL
   - test_liqpay_callback_success — симулює коректний LiqPay callback, bill стає 'paid'
   - test_liqpay_callback_invalid_signature — повертає 400
   - test_stripe_webhook — симулює Stripe checkout.session.completed
   - test_only_owner_can_checkout — чужий мешканець отримує 403

=== ФРОНТЕНД ===

Сторінка /billing — кнопка "Оплатити онлайн":
- POST /checkout/ → отримує checkout_url → window.location.href = checkout_url
- Після повернення з LiqPay: GET /payment-status/ (polling 2 сек, макс 30 сек)
- Показати результат: ✅ "Оплату успішно проведено" або ❌ "Помилка оплати, спробуйте ще"
- Стан "Обробляється..." під час polling

Компонент `PayButton` в `client/src/components/billing/PayButton.tsx`.
```

---

### 🗣️ ФІЧА 4 — Форум мешканців

**Статус:** `[ ] не розпочато`

**Промт для розробки:**

```
Додай форум мешканців до Django Apartment Management.

=== БЕКЕНД ===

1. Нова app `server/apps/forum/`:

   Моделі:

   a) `ForumCategory`:
      - name: CharField (Загальні питання, Ремонт, Сусіди, Паркінг, Безпека)
      - slug: AutoSlugField
      - description: TextField
      - building: FK → Building (null=True — загальний або для конкретного будинку)
      - order: IntegerField(default=0)
      - is_active: BooleanField(default=True)

   b) `ForumThread` — тема:
      - category: FK → ForumCategory
      - author: FK → Profile
      - title: CharField(max_length=255)
      - slug: AutoSlugField(populate_from='title')
      - body: TextField
      - is_pinned: BooleanField(default=False) — закріплена тема
      - is_locked: BooleanField(default=False) — заблокована (тільки адмін може додавати)
      - is_anonymous: BooleanField(default=False) — автор прихований
      - views_count: IntegerField(default=0)
      - replies_count: IntegerField(default=0) — денормалізовано для швидкості
      - last_reply_at: DateTimeField(null=True)
      - created_at, updated_at

   c) `ForumReply` — відповідь:
      - thread: FK → ForumThread
      - author: FK → Profile
      - body: TextField
      - parent: FK → self (null=True) — для вкладених відповідей (1 рівень)
      - is_solution: BooleanField(default=False) — позначено як вирішення
      - is_anonymous: BooleanField(default=False)
      - created_at, updated_at

   d) `ForumReaction`:
      - content_type: FK → ContentType (generic для Thread і Reply)
      - object_id: UUIDField
      - user: FK → User
      - reaction: CharField choices=['like', 'dislike', 'helpful']
      - unique_together: (content_type, object_id, user)

2. API:
   - GET /api/v1/forum/categories/ — список категорій (фільтр by building)
   - GET /api/v1/forum/threads/?category=&search=&ordering= — список тем з пагінацією
   - POST /api/v1/forum/threads/ — створити тему (IsAuthenticated)
   - GET /api/v1/forum/threads/{slug}/ — деталь теми + інкремент views_count
   - PATCH /api/v1/forum/threads/{slug}/ — редагувати (тільки автор або admin)
   - DELETE /api/v1/forum/threads/{slug}/ — видалити (тільки автор або admin)
   - GET /api/v1/forum/threads/{slug}/replies/ — відповіді (пагінація)
   - POST /api/v1/forum/threads/{slug}/replies/ — додати відповідь
   - PATCH /api/v1/forum/replies/{id}/ — редагувати
   - DELETE /api/v1/forum/replies/{id}/ — видалити
   - POST /api/v1/forum/threads/{slug}/react/ — { reaction: 'like' }
   - POST /api/v1/forum/replies/{id}/react/ — аналогічно
   - POST /api/v1/forum/replies/{id}/mark-solution/ — позначити як вирішення (автор теми)

3. Права доступу:
   - Читати: всі authenticated
   - Писати: тільки мешканці свого будинку (перевіряти через unit.entrance.building)
   - Адмін: pin/lock/delete будь-що

4. Сигнали:
   - Після ForumReply.save() → інкрементувати thread.replies_count, оновити thread.last_reply_at
   - Надіслати Telegram нотифікацію автору теми: "💬 {username} відповів на вашу тему '{title}'"

5. Тести (test_forum.py):
   - test_create_thread — POST /threads/
   - test_reply_increments_count — перевірка денормалізованого лічильника
   - test_cross_building_access — мешканець іншого будинку отримує 403
   - test_mark_solution — тільки автор теми може позначити

=== ФРОНТЕНД ===

Сторінки:
- /forum — список категорій з лічильниками тем/відповідей
- /forum/[category-slug] — теми категорії (картки з автором, датою, replies_count)
- /forum/[category-slug]/[thread-slug] — деталь теми + відповіді + форма відповіді
- Кнопка "Нова тема" → модальне вікно (заголовок, тіло, категорія)
- Реакції (👍 like, 👎 dislike) на кожній відповіді
- Позначка ✅ Solution на правильній відповіді

Навігація: додати "Форум" до LeftNavbar поруч із постами.

Redux: `forumApiSlice` в `client/src/lib/redux/features/forum/`.
```

---

### 🗳️ ФІЧА 5 — Питання до керуючої компанії + Голосування

**Статус:** `[ ] не розпочато`

**Промт для розробки:**

```
Додай модуль питань мешканців до керуючої компанії з системою голосування
до Django Apartment Management.

Правило: якщо питання набирає ≥ 1000 голосів → статус "high_priority",
керуюча компанія зобов'язана відповісти протягом 72 годин.

=== БЕКЕНД ===

1. Нова app `server/apps/qa/` (або розшир apps/posts/):

   Моделі:

   a) `Question`:
      - author: FK → Profile
      - building: FK → Building (null=True — для всього ЖК або конкретного будинку)
      - title: CharField(max_length=300)
      - body: TextField
      - slug: AutoSlugField
      - status: CharField choices=[
          'open',           # нове питання
          'high_priority',  # ≥1000 голосів
          'answered',       # є офіційна відповідь
          'closed'          # закрито адміном
        ]
      - votes_count: IntegerField(default=0) — денормалізовано
      - priority_reached_at: DateTimeField(null=True) — коли набрало 1000
      - answer_deadline: DateTimeField(null=True) — priority_reached_at + 72h
      - is_anonymous: BooleanField(default=False)
      - created_at, updated_at

   b) `QuestionVote`:
      - question: FK → Question
      - user: FK → User
      - created_at: DateTimeField(auto_now_add=True)
      - unique_together: (question, user) — один голос від юзера

   c) `OfficialAnswer`:
      - question: FK → Question (OneToOne)
      - answered_by: FK → Profile (staff/admin)
      - body: TextField
      - created_at: DateTimeField(auto_now_add=True)
      - updated_at: DateTimeField(auto_now=True)
      - attachments: ManyToMany → Media (опційно)

2. Логіка голосування (`qa/services.py`):
   def vote_for_question(user, question_id) -> Question:
       - Якщо вже голосував — raise AlreadyVotedError (400)
       - Якщо питання closed — raise ClosedError (400)
       - QuestionVote.objects.create(question=q, user=user)
       - q.votes_count = F('votes_count') + 1; q.save()
       - Перевірка порогу:
         if q.votes_count >= 1000 and q.status == 'open':
             q.status = 'high_priority'
             q.priority_reached_at = now()
             q.answer_deadline = now() + timedelta(hours=72)
             q.save()
             notify_admins_high_priority(q)  # Telegram + Email

3. API:
   - GET /api/v1/qa/questions/?status=&building=&ordering=votes_count — список
   - POST /api/v1/qa/questions/ — задати питання (IsAuthenticated)
   - GET /api/v1/qa/questions/{slug}/ — деталь
   - POST /api/v1/qa/questions/{slug}/vote/ — проголосувати
   - DELETE /api/v1/qa/questions/{slug}/vote/ — зняти голос
   - GET /api/v1/qa/questions/{slug}/voted/ — чи я вже голосував?

   Адмін (IsAdminUser):
   - POST /api/v1/qa/questions/{slug}/answer/ — додати офіційну відповідь
   - PATCH /api/v1/qa/questions/{slug}/answer/ — оновити відповідь
   - PATCH /api/v1/qa/questions/{slug}/status/ — закрити питання

4. Celery tasks:
   - `check_overdue_answers()` — щогодини: знаходить high_priority де answer_deadline < now() і немає відповіді → Telegram адмінам "⚠️ ПРОСТРОЧЕНО: питання '{title}' ще без відповіді!"
   - `notify_question_author_answered(question_id)` — Telegram автору коли з'явилась відповідь

5. Django Admin:
   - QuestionAdmin: фільтри за статусом, лічильник голосів, кнопка "Відповісти"
   - Виділення high_priority червоним кольором (get_list_display color)

6. Тести (test_qa.py):
   - test_vote_increments_count
   - test_duplicate_vote_rejected
   - test_threshold_triggers_high_priority — при 1000-му голосі статус змінюється
   - test_answer_deadline_set — перевірка що deadline = priority_reached_at + 72h
   - test_admin_can_answer
   - test_overdue_task_notifies

=== ФРОНТЕНД ===

Сторінки:
- /questions — список питань (фільтр: Всі / Гарячі ≥100 голосів / Пріоритетні / Відповідені)
- /questions/[slug] — деталь: текст, кнопка голосування, прогрес-бар (X / 1000), офіційна відповідь
- Кнопка "Задати питання" → форма (заголовок, текст, будинок)
- Значок 🔥 для high_priority, таймер зворотного відліку до answer_deadline

Компонент `VoteButton`:
- Показує поточну кількість голосів
- Анімація +1 при кліку
- Прогрес-бар до 1000 (зелений до 500, жовтий 500-800, червоний 800-1000, синій після 1000)
- Disabled якщо вже голосував (підсвічений)

Redux: `qaApiSlice` в `client/src/lib/redux/features/qa/`.
```

---

### 📢 ФІЧА 6 — Публікації від керуючої компанії (CMS)

**Статус:** `[ ] не розпочато`

**Промт для розробки:**

```
Покращ систему оголошень (Announcement) до повноцінного CMS-модуля
для публікацій керуючої компанії в Django Apartment Management.

=== БЕКЕНД ===

1. Розшир існуючу модель `posts/Announcement`:
   - Додати поля:
     - `category`: CharField choices=['news', 'maintenance', 'emergency', 'event', 'finance']
     - `priority`: IntegerField choices=[1=normal, 2=important, 3=urgent]
     - `cover_image`: ImageField (MinIO upload)
     - `attachments`: ManyToMany → 'posts.Attachment' (файли PDF, DOCX)
     - `published_at`: DateTimeField(null=True) — null = чернетка
     - `expires_at`: DateTimeField(null=True) — оголошення автоматично деактивується
     - `views_count`: IntegerField(default=0)
     - `author`: FK → Profile (staff)
   - Нова модель `Attachment`:
     - file: FileField (upload_to='announcements/attachments/')
     - name: CharField
     - size: IntegerField
     - mime_type: CharField

2. API:
   Публічний (IsAuthenticated):
   - GET /api/v1/announcements/ — список активних (published_at <= now, expires_at > now або null)
     Фільтри: building, category, priority, ?search=
     Сортування: -published_at (за замовчуванням)
   - GET /api/v1/announcements/{slug}/ — деталь + інкремент views_count

   Адмін (IsAdminUser):
   - POST /api/v1/announcements/ — створити (підтримка multipart/form-data для файлів)
   - PATCH /api/v1/announcements/{slug}/ — оновити
   - DELETE /api/v1/announcements/{slug}/ — видалити (soft delete: is_active=False)
   - POST /api/v1/announcements/{slug}/publish/ — змінити published_at = now()
   - POST /api/v1/announcements/{slug}/unpublish/ — published_at = null
   - POST /api/v1/announcements/attachments/ — завантажити файл → { id, url }

3. Celery:
   - `expire_announcements()` — щогодини: is_active=False для expires_at < now()
   - `notify_new_announcement(announcement_id)` — після публікації → Telegram всім мешканцям будинку:
     "📢 Нове оголошення від керуючої компанії: '{title}'\nЧитати: {url}"

4. Тести:
   - test_draft_not_visible_to_tenant — unpublished не доступне через публічний API
   - test_publish_action — POST /publish/ робить оголошення видимим
   - test_expiry_task — Celery task деактивує прострочені
   - test_attachment_upload

=== ФРОНТЕНД ===

Мешканець:
- /announcements — стрічка новин: картки з обкладинкою, категорією, пріоритетом
  - Бейдж 🚨 ТЕРМІНОВО для priority=3
  - Фільтр за категорією (таби)
- /announcements/[slug] — детальна публікація з вкладеннями (кнопки завантаження)

Адмін (/admin/posts — покращ існуючу сторінку):
- Rich text editor для body (підключи TipTap або react-quill)
- Drag-and-drop для cover_image
- Завантаження файлів-вкладень (PDF, DOCX)
- Вибір: Чернетка / Опублікувати зараз / Заплановано (published_at у майбутньому)
- Вибір будинків (мультиселект)
- Попередній перегляд публікації

Redux: розшир `adminApiSlice` або створи `announcementsApiSlice`.
```

---

### 📰 ФІЧА X — Новини порталу (News)

**Статус:** `[x] завершено`

- [x] Новини порталу (News) — модель, API, frontend /news
- [x] ComingSoon компонент для мікросервісів (payments, contacts)
- [x] Перейменування: Оголошення → Новини в навігації

---

### 🔔 ФІЧА 7 — Нотифікації робітникам при призначенні задачі

**Статус:** `[ ] не розпочато`

**Промт для розробки:**

```
Додай систему нотифікацій для робітників/технічного персоналу
при призначенні заявки в Django Apartment Management.

Передумова: ФІЧА 1 (Telegram) бажана, але не обов'язкова.

=== БЕКЕНД ===

1. Розшир модель `issues/Issue`:
   - Переконатись що є поле `assigned_to`: FK → Profile (null=True, blank=True)
   - Додати: `assigned_at`: DateTimeField(null=True)
   - Додати: `assignment_note`: TextField(null=True) — коментар диспетчера при призначенні

2. API для призначення:
   - PATCH /api/v1/issues/{id}/assign/:
     Body: { assigned_to: "profile_slug", assignment_note: "..." }
     Права: IsAdminUser або IsDispatcher
     Логіка:
       - Встановити assigned_to, assigned_at = now(), assignment_note
       - Якщо статус 'reported' → автоматично перевести в 'accepted'
       - Викликати notify_worker_assigned.delay(issue_id)
       - Повернути оновлений issue

   - DELETE /api/v1/issues/{id}/assign/ — зняти призначення (reassign)

3. Celery tasks (`issues/tasks.py`):

   a) `notify_worker_assigned(issue_id)`:
      - Завантажити issue з assigned_to profile
      - Email: тема "Вам призначено нову заявку #{{id}}", тіло з деталями (адреса, категорія, SLA deadline, коментар)
      - Якщо є TelegramProfile і is_verified:
        "🔧 Вам призначено заявку #{{id}}
        📍 Адреса: {{unit}}
        🏷️ Категорія: {{category}}
        ⏰ Термін: {{due_at}}
        📝 {{assignment_note}}
        Переглянути: {{url}}"

   b) `notify_worker_approaching_deadline(issue_id)`:
      - За 2 години до due_at: нагадування якщо статус ще 'in_progress' або 'accepted'
      - Telegram: "⚠️ Заявка #{{id}} — до дедлайну залишилось 2 години!"

   c) `schedule_deadline_reminders()` — Celery beat: щогодини знаходить заявки де due_at - now() < 2h, ставить notify_worker_approaching_deadline в чергу якщо ще не надіслано (використати Redis set для дедуплікації)

4. Розшир Django Admin:
   - В `IssueAdmin` — дія "Призначити виконавця" (вибір з dropdown активних робітників)
   - Колонка "Призначено" з посиланням на профіль
   - Фільтр "Непризначені"

5. Права:
   - IsDispatcher: новий permission клас — staff або has_perm('issues.assign_issue')
   - Додати `class Meta: permissions = [("assign_issue", "Can assign issues")]` в модель Issue

6. Тести (test_assignment.py):
   - test_assign_issue_changes_status — автоматичний перехід reported→accepted
   - test_assign_triggers_celery_task — mock Celery, перевірити виклик
   - test_telegram_notification_sent — mock httpx, перевірити текст
   - test_non_dispatcher_cannot_assign — 403
   - test_deadline_reminder_scheduled

=== ФРОНТЕНД ===

Адмін-панель /admin/issues:
- Колонка "Виконавець": показати аватар + ім'я або "Не призначено"
- Кнопка "Призначити" → модальне вікно:
  - Dropdown: список активних робітників (з фільтром за спеціалізацією)
  - Поле для коментаря
  - Кнопка підтвердження
- Bulk assign: вибір кількох заявок → призначити одному робітнику

Сторінка робітника /my-tasks (нова):
- Список заявок, призначених поточному юзеру
- Фільтр: Нові / В роботі / Виконані / Прострочені
- Кнопки переходу статусу прямо зі списку
- Таймер до дедлайну (червоний якщо < 2 год)

Redux: додай `assignApiSlice` або розшир `issueApiSlice` мутаціями `assignIssue`, `unassignIssue`.
Додай `useGetMyTasksQuery` для сторінки робітника.
```

---

## Backend — існуючий борг

### Критичне

- [x] **Перейменувати `TIME_ZONE`** з `"Asia/Kolkata"` на `"Europe/Kyiv"` у `base.py` (вже було)
- [x] **Вʼязка Unit ↔ Profile**: `unit` FK (для мешканця) + `building` FK (для диспетчера) у Profile + міграція 0006
- [x] **Права доступу на заявки**: суперюзер — всі; staff з building → тільки свій будинок; мешканець → тільки власні (`/my-issues/`)
- [x] **Фільтрація та сортування заявок**: `IssueFilter` по status/priority/category/building/is_overdue + search + ordering

### DevOps / Інфраструктура

- [ ] **`.env.example`**: шаблон усіх змінних оточення
- [ ] **GitHub Actions CI**: `pytest`, `ruff`, `mypy` при кожному PR
- [ ] **Production docker-compose**: Gunicorn + окремий nginx для static
- [ ] **Backup скрипт** для PostgreSQL (pg_dump → MinIO)
- [ ] **Sentry** для моніторингу помилок у продакшні
- [ ] **SSL / HTTPS** конфіг для nginx

### Технічний борг

- [x] Видалити `apartment_unit` (legacy field) — фронт перейшов на `unit_number`
- [x] Замінити `apartment` FK в `IssueStatusUpdateSerializer` на `unit_number`
- [x] Health checks для Docker контейнерів (postgres, redis, minio, server, celery)
