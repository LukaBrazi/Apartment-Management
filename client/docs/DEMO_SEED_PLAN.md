# Демо-ЖК для прода — план повного перероблення `seed_demo`

> Статус: draft, потребує review від backend lead + product
> Автор: Жукуймося team (QA + client devs), 2026-04-18
> Мета: замінити поточний `seed_demo` на production-ready демо-наповнення, яке щодоби о **23:00 за Києвом** скидається до чистого стану, не залежить від людського рукоприкладства і демонструє **весь** функціонал ApartmentOS у естетичному вигляді.

> **Скоуп (уточнено з продуктом 2026-04-18):**
> - Без субдомену, без мульти-тенантності — демо живе як **ще один Building** на існуючому проді.
> - Клієнтам роздаємо креди **директор (диспетчер) / охоронець / мешканець** — Django superuser **ніколи не експонується**.
> - Один cron щодоби о 23:00 Europe/Kyiv зносить усе що створили клієнти і заново засіває.
> - Без `Organization` моделі — достатньо маркерів (email-домен `@demo.com` + slug будинку) і scoped delete.

---

## 0. TL;DR — що змінюється і чому

Поточний стан:
- `seed_demo` створює мінімум (кілька юзерів, один будинок, 6 постів, 5 тегів) і має дірки: не створює жодного `Issue`, `VehiclePass`, `Rating`, `Announcement`.
- `tenant@demo.com` після повторного сіду лишається з `apartment=null`, що ламає `GET /profiles/user/my-profile/` (500).
- `GET /profiles/admin/all/` стабільно падає з 500.
- Дані стрічкові, нецікаві для показу: без варіативності статусів, без фото, без пагінації.

Чого досягаємо:
- У проді живе окремий Building «Зелений Квартал — Демо» з власним набором юзерів на `@demo.com` домені.
- Клієнт, якому ми показуємо продукт, отримує 3 пари креденшлів (director / guard / resident), заходить і бачить *повний* функціонал — адмінку, заявки, перепустки, пости, рейтинги.
- Щодня о 23:00 Києва K8s CronJob запускає `manage.py seed_demo --reset`, який **scoped** (по email-домену + slug будинку) знищує всі демо-дані і сіє заново. Клієнт написав щось непристойне у пості — до ранку цього вже нема.
- Дані варіативні, з українськими реалістичними іменами, обсяг демонструє пагінацію, сортування, фільтри, історію — усе, що має сенс показати клієнту.
- **Superuser (Django admin)** не входить у демо-скоуп — створюється окремо через `createsuperuser`, захищений `is_superuser=False` фільтром у reset'і, щоб випадково не знести адмін-акаунт.

Розміри за замовчуванням (налаштовуються прапорами команди):

| Сутність | Скільки | Примітки |
|---|---|---|
| Buildings | 1 | «Зелений Квартал — Демо», Київ, `slug="demo-zelenyi-kvartal"` |
| Entrances | 3 | «А», «Б», «В» |
| Units | 48 | 8 поверхів × 2 під'їзди × 3 квартири, 1 під'їзд резервний |
| Dispatchers (director) | 2 | 2 зміни — showcase мульти-адмін |
| Guards | 3 | 3 зміни / вихідні |
| Workers | 8 | plumber, electrician, carpenter, mason, roofer, painter, hvac, painter2 |
| Residents | 32 | 30 прив'язані до Unit'ів, 2 без Unit (для флоу «admin binds apartment») |
| Issues | 45 | Mix of statuses/priorities (див. §5) |
| Posts | 18 | З реплаями, upvotes, viewcount |
| Tags | 12 | Seed-стабільний набір |
| Announcements | 5 | 3 активні, 2 архівні |
| VehiclePasses | 22 | Mix of pending/closed, різні дати |
| Ratings | 35 | На workers, різні 1-5 зірок |
| Replies | 40 | Розкидані по Posts |

---

## 1. Принципи

Кожен принцип — один абзац, щоб не залишати простору для інтерпретації.

**Ідемпотентність.** Повторний запуск команди без `--reset` дає ідентичний результат (жодних дублікатів, жодних додавань). Досягається через `update_or_create` з натуральними ключами (email/slug для юзерів, `building.slug + unit_number` для квартир, генерований детермінований UUID через `uuid.uuid5(namespace, natural_key)`).

**Детермінізм.** `Faker.seed(42)` на старті, `random.seed(42)`, стабільний namespace для UUID'ів. Два послідовних запуски без змін коду → той самий output, аж до timestamp'ів (використовуємо фіксований `base_time = 2026-04-01T09:00:00+03:00` Europe/Kyiv і зсуви від нього).

**Атомарність.** Все у `transaction.atomic()`. Будь-яка помилка посередині — повний rollback. Краще exit 1 + Sentry alert, ніж залишити БД у полузасіяному стані.

**Ізоляція (через маркери, не через FK).** Демо-скоуп визначається двома незалежними маркерами:
1. Усі демо-юзери мають email на домені `@demo.com`.
2. Демо-будинок має фіксований slug `demo-zelenyi-kvartal`.

Reset-скрипт чіпає **тільки** об'єкти, що відповідають цим маркерам. Реальні користувачі (інший домен) і реальні будинки (інший slug) гарантовано не постраждають. Коли/якщо бізнес виросте у мульти-тенантний SaaS — мігруємо на `Organization` FK окремим ADR, але поки що це надлишкова складність.

**Клієнто-безпека.**
- **Superuser `is_superuser=True` ніколи не роздається і ніколи не потрапляє в reset** (явний `is_superuser=False` у queryset'і видалення).
- Клієнту видаються тільки ролі: директор (диспетчер), охоронець, мешканець. Workers — опційно (див. §4).
- Пароль демо-юзерів з env `DEMO_PASSWORD` (секрет у K8s), локально — `Demo1234!`.
- Нічний reset о 23:00 підстрахує від будь-якого небажаного контенту, який клієнт міг залишити за день.

**Естетика.** Усі поля мають сенс: адреси реальні київські, авто-номери українського формату (АА1234ВВ кирилицею), імена з наших справжніх українських name pool'ів, аватарки — стабільні посилання на DiceBear за seed'ом.

**Модульність.** `seed_demo` — не один великий скрипт, а оркестратор, який викликає `seed_building`, `seed_users`, `seed_issues`, `seed_posts`, `seed_passes`, `seed_ratings`. Кожен з них самодостатній, тестований юніт-тестом, може бути запущений окремо під час розробки нового модуля.

---

## 2. Архітектурний контекст (без нових моделей)

У поточному стані продукт ефективно single-tenant: один Django instance обслуговує один набір будинків і юзерів. Демо-ЖК = **просто ще один Building** у тій самій БД. Немає потреби ні в субдомені, ні в Organization моделі — вистачає двох маркерів (email-домен `@demo.com` + slug будинку).

**Scoped reset без нових FK:**
- `User.objects.filter(email__iendswith="@demo.com", is_superuser=False).delete()` — каскадно зносить Profile, Issues (author FK), VehiclePasses (tenant FK), Posts (author FK), Ratings (from_user FK), Replies, Bookmarks.
- `Building.objects.filter(slug="demo-zelenyi-kvartal").delete()` — каскадно зносить Entrances, Units, Announcements (FK на Building).
- Tags — глобальні, не чіпаємо (якщо не використовуються ніде крім демо-постів, вони залишаться сирітками — окремий cleanup у §11).

**Безпекові запобіжники** (див. §11) гарантують, що реальні юзери (якщо вони з'являться на проді) і суперюзер ніколи не попадають у queryset видалення.

Якщо пізніше захочемо повноцінну мульти-тенантність (SaaS з ізоляцією per customer) — це буде окремий ADR «Introducing Organization model» і окремий спринт роботи. На сьогодні це надлишкова складність, яка коштує 2+ тижні бекенд-часу без видимого для клієнта effect'у.

---

## 3. Структура демо-ЖК

### 3.1 Building

```python
Building(
    slug="demo-zelenyi-kvartal",        # STABLE — reset фільтр спирається на нього
    name="Зелений Квартал — Демо",
    address="вул. Академіка Заболотного, 15",
    city="Київ",
    complex_name="ЖК Зелений Квартал",
    is_active=True,
)
```

`slug` — єдине поле, за яким reset знаходить будинок. Перейменування заборонено без одночасного оновлення `_reset_demo_scope.py` (є юніт-тест, що асертить стабільність).

### 3.2 Entrances

Три під'їзди — «А», «Б», «В». У адмінці показує селект з реальним вибором, у перепустках показує реальні назви.

### 3.3 Units (квартири)

48 юнітів загалом:
- Під'їзд А: поверхи 1-8, по 3 квартири на поверх → 24 юніти, номери 101-803
- Під'їзд Б: поверхи 1-8, по 3 квартири на поверх → 24 юніти, номери 101-803
- Під'їзд В: 0 юнітів (резерв на майбутнє, показує що структура підтримує порожні під'їзди)

Номер формули: `f"{floor}{unit_on_floor:02d}"` → 101, 102, 103, 201, 202, 203... (класика українських ЖК).

Спеціальні юніти:
- А-105 — закріплений за `tenant@demo.com` (для сумісності з існуючими тестами).
- А-207 і Б-308 — **вакантні**, не прив'язані ні до кого; щоб у адмінці був сценарій «створити мешканця + прив'язати до вільної квартири».

---

## 4. Користувачі

Таблиця повна. Пароль у всіх — `Demo1234!` локально, на проді — з env `DEMO_PASSWORD`, секрет у K8s.

> ⚠️ **Superuser (Django admin) у цю таблицю не входить.** Його створює DevOps через `createsuperuser` один раз на початку, email — з корпоративного домену (не `@demo.com`), не роздається клієнтам.

| Email | Роль | Ім'я | Юніт | occupation | is_staff | Коментар |
|---|---|---|---|---|---|---|
| `dispatcher@demo.com` | **Директор** (диспетчер) | Тетяна Романенко | — | tenant | True | **Роздаємо клієнту** — головна showcase-роль |
| `dispatcher2@demo.com` | Диспетчер | Олег Степаненко | — | tenant | True | Друга зміна; показує що система розрахована на кількох адмінів |
| `guard@demo.com` | **Охоронець** | Микола Гвоздюк | — | guard | False | **Роздаємо клієнту** — guard portal showcase |
| `guard2@demo.com` | Охоронець | Андрій Лук'яненко | — | guard | False | Друга зміна |
| `guard3@demo.com` | Охоронець | Петро Савчук | — | guard | False | Вихідні |
| `plumber@demo.com` | Сантехнік | Василь Мельник | — | plumber | False | Опціонально — роздаємо якщо хочемо показати assignee flow з боку worker'а |
| `electrician@demo.com` | Електрик | Ігор Кравченко | — | electrician | False | — |
| `carpenter@demo.com` | Тесляр | Степан Бойко | — | carpenter | False | — |
| `mason@demo.com` | Муляр | Петро Коваленко | — | mason | False | — |
| `roofer@demo.com` | Покрівельник | Сергій Павленко | — | roofer | False | — |
| `painter@demo.com` | Маляр | Марія Іваницька | — | painter | False | — |
| `hvac@demo.com` | HVAC майстер | Валерій Середа | — | hvac | False | — |
| `painter2@demo.com` | Маляр | Наталія Борисюк | — | painter | False | Для варіативності в assign-flow |
| `tenant@demo.com` | **Мешканець** | Іван Тестовий | А-105 | tenant | False | **Роздаємо клієнту** — showcase resident view |
| `resident1@demo.com` … `resident8@demo.com` | Мешканці | українські імена (див. 4.2) | А-101..А-108 | tenant | False | Для флоу з кількома юзерами |
| `resident9@demo.com` … `resident22@demo.com` | Мешканці | українські імена | А-109..А-124, Б-201..Б-206 | tenant | False | Наповнення, щоб списки пагінувалися |
| `new1@demo.com` | Мешканець (без квартири) | Олена Нова | — | tenant | False | Для «admin binds apartment» демо |
| `new2@demo.com` | Мешканець (без квартири) | Роман Підполковник | — | tenant | False | Те саме |

### 4.1 Що саме роздається клієнту

Мінімальний «демо-pack», який надсилаємо email'ом sales'а:

```
ЖК «Зелений Квартал» — демо-доступ
──────────────────────────────────
Директор / Диспетчер:
  dispatcher@demo.com  /  <DEMO_PASSWORD>
Охоронець:
  guard@demo.com       /  <DEMO_PASSWORD>
Мешканець:
  tenant@demo.com      /  <DEMO_PASSWORD>

⚠️ Дані скидаються щодня о 23:00 за Києвом.
   Не зберігайте у демо нічого цінного.
```

Інші юзери (resident2..22, workers) — існують у БД для реалістичного наповнення списків, але креди ми їх не роздаємо, щоб не плутати клієнта.

### 4.2 Генерація аватарок

Використовуємо **DiceBear v7** з стабільним seed (email):
```
https://api.dicebear.com/7.x/initials/svg?seed={email}&backgroundColor=1e88e5,43a047,fb8c00
```
Плюси: SVG, легкий, стабільний, не залежить від сторонніх картинок. Можна замінити на `adventurer` або `micah` style для більш «людських» облич.

### 4.3 Український name pool

Імена повинні бути реалістичні. Faker `uk_UA` дає базу, але для директора і охоронців краще вручну фіксуємо якісні пари (список див. у §13 в python code).

### 4.4 Поля профілю

Для кожного резидента заповнюємо:
- `first_name`, `last_name`, `username` (`{first}_{last}` транслітеровано)
- `phone_number` — `+380` + випадкові 9 цифр з фіксованим seed
- `gender` — `random.choice(["male", "female"])`
- `country_of_origin = "Ukraine"`
- `city_of_origin` — `random.choice(["Київ", "Львів", "Одеса", "Харків", "Дніпро", "Чернігів"])`
- `bio` — 1-2 речення (українські, Faker.sentence(nb_words=10, locale="uk_UA"))
- `reputation` — починаємо з 0, до workers додаємо 10-50 після створення ratings
- `date_joined` — `base_time - timedelta(days=random.randint(30, 400))`

---

## 5. Заявки (Issues) — найголовніша демка

45 заявок, які покривають **усі статуси, пріоритети, сценарії**. Це найважливіший показ, тому тут не економимо.

### 5.1 Розподіл за статусами

| Status | Кількість | Коментар |
|---|---|---|
| `reported` | 12 | 8 unassigned + 4 assigned to worker, не почав |
| `accepted` | 10 | Прийняті, очікують виконання |
| `in_progress` | 8 | У роботі, з призначеним виконавцем |
| `done` | 10 | Виконані, з resolved_by + resolved_on |
| `rejected` | 5 | Відхилені з коментарем |

Такий розподіл показує: нових заявок більше (реалістично), виконаних трохи менше, відхилених — поодинокі.

### 5.2 Розподіл за пріоритетами

| Priority | Кількість | Коментар |
|---|---|---|
| `low` | 18 | Побутове |
| `medium` | 20 | Основна маса |
| `high` | 7 | Справжня терміновість |

### 5.3 Overdue (прострочені)

3 заявки з `status in [accepted, in_progress]` і `created_at = base_time - 14 days` — щоб `is_overdue` прапор спрацював і у UI підсвітився червоним. Крихкий момент: `is_overdue` має бути property або SerializerMethodField на сервері (не поле у БД), тоді воно обчислюється від created_at автоматично.

### 5.4 View counts

Varied: `reported` — 1-3 перегляди, `in_progress` — 10-30, `done` — 20-80. Показує що старі заявки дивляться більше.

### 5.5 Реалістичні тайтли і описи

Український pool (частковий, повний у коді `_seed_issues.py`):
```
("Протікає кран на кухні",                "Холодна вода, капає з крана. Ручка лежить вільно."),
("Не працює ліфт у під'їзді А",           "З ранку стоїть, не відкриває двері. Кнопки не світяться."),
("Перегоріла лампа на 3-му поверсі",      "Сходова клітка, лампа біля 302-ї квартири."),
("Тріщина у стелі ванної кімнати",         "З'явилась після сусідів зверху, протікає."),
("Не закриваються вхідні двері",           "Замок не клацає, доводиться штовхати."),
("Шум у вентиляції",                       "Вдень і вночі, у спальні."),
("Стеля провисла у коридорі",              "Здається, буде падати, страшно."),
("Запах каналізації з ванної",             "Посилюється ввечері, треба перевірити."),
("Батарея холодна у вітальні",             "Інші теплі, лише одна. Сезон."),
("Зламались ворота парковки",              "Не опускаються, машини стоять."),
("Домофон не відповідає",                  "Квартира Б-208, мовчить."),
("Тарган у квартирі",                      "Гидко. Треба дезінсекцію."),
# ...більше різноманіття, щоб усі 45 були унікальні
```

### 5.6 Assignment

Workers розподілені пропорційно occupation:
- Сантехнічні заявки → plumber
- Електрика → electrician
- Муляр роботи → mason
- Etc.

У `in_progress` і `done` — 100% assigned. У `accepted` — 60% assigned, 40% ще чекає. У `reported` — 30% assigned (проактивне призначення).

### 5.7 created_at / updated_at timeline

Рівномірно розподілений у `base_time - 30 days ... base_time - 1 day`. У `done` — `resolved_on` = `created_at + timedelta(days=random.randint(1, 7))`.

---

## 6. Пости і теги

### 6.1 Теги (12)
```
правила, ремонт, заявки, інструкція, перепустки, електрика,
сантехніка, прибирання, опалення, паркування, безпека, новини
```

### 6.2 Пости (18)

Кожен пост має: title, body (3-5 абзаців українською, Faker.text), author_username (з диспетчера або residents), view_count (50-500), upvotes (0-40), downvotes (0-10), 1-4 теги, 0-4 reply.

Теми:
1. «Правила паркування на території ЖК» (правила, паркування) — closed topic, 50 upvotes
2. «Як правильно подавати заявку на ремонт» (інструкція, заявки, ремонт) — evergreen
3. «Графік роботи сантехніка» (сантехніка, інструкція)
4. «Економія електроенергії: поради для мешканців» (електрика)
5. «Підготовка до опалювального сезону» (опалення)
6. «Нові правила сортування сміття» (правила)
7. «Оновлення системи перепусток — що нового» (перепустки, новини)
8. «Як скликати загальні збори мешканців» (правила)
9. «Безпека у багатоквартирному будинку: гайд» (безпека, інструкція)
10. «Що робити, якщо сусіди шумлять» (правила)
11. «Ремонт у квартирі: дозволені години робіт» (ремонт, правила)
12. «Нові камери на під'їздах — інформація» (безпека, новини)
13. «Паркінг підземний: інструкція користування» (паркування, інструкція)
14. «Як викликати аварійну службу вночі» (заявки, інструкція)
15. «Графік прибирання сходових кліток» (прибирання)
16. «FAQ — поширені питання мешканців» (інструкція)
17. «Благодійний захід на День Незалежності» (новини)
18. «Звіт керуючої компанії за I квартал 2026» (новини)

### 6.3 Replies

На кожен 2-3 пост — 1-4 репляу. Приклади:
- «Дякую, дуже корисно!»
- «А чи є довідник контактів?»
- «Супер, нарешті зрозуміло.»
- «Підтримую, давно пора»

### 6.4 Bookmarks, upvotes

Частина residents має bookmarked 3-5 постів (для showcase табу «Закладки» у профілі).

---

## 7. Announcements (повідомлення у новинах)

5 штук, усі прикріплені до нашого Building.

| # | Title | Active | Створена |
|---|---|---|---|
| 1 | «Планове відключення води 21.04.2026 з 10:00 до 14:00» | True | base_time - 2d |
| 2 | «Завтра обробка під'їздів дезінфектором» | True | base_time - 1d |
| 3 | «Графік роботи консьєржа на травневі свята» | True | base_time - 5d |
| 4 | «АРХІВ: Відключення світла 12.03.2026» | False | base_time - 40d |
| 5 | «АРХІВ: Обробка проти щурів 01.02.2026» | False | base_time - 75d |

---

## 8. Перепустки (VehiclePasses)

22 штуки, різноманітний mix:

| Вид | Кількість | Деталі |
|---|---|---|
| pending, майбутні (next 7 days) | 8 | Різні tenants, авто `АА1234ВВ` формат |
| pending, на сьогодні | 3 | Для show-case guard flow |
| closed, закриті сьогодні | 4 | `closed_by=guard@demo.com` |
| closed, за останній тиждень | 5 | Різні guards |
| closed, старі (30+ днів) | 2 | Для архіву |

Приклади:
```
tenant=resident1, car=АА1234КВ, visit_date=today+2d, comment="Привезуть меблі"
tenant=resident5, car=ВС5678АА, visit_date=today, comment="Гості на день народження"
tenant=resident12, car=АІ9876БХ, visit_date=today-3d, status=closed, closed_by=guard
```

Генерування українських номерів:
```python
"".join(random.choices("АВЕКМНОРСТУХ", k=2)) + f"{random.randint(1000, 9999)}" + "".join(random.choices("АВЕКМНОРСТУХ", k=2))
```
(Використовуємо кирилицю, яка візуально схожа на латиницю — український автономерний стандарт.)

---

## 9. Рейтинги

Кожен worker отримує 3-6 рейтингів від residents.
- plumber: середній 4.8 (showcase топового спеца)
- electrician: 4.5
- carpenter: 4.2
- mason: 3.8
- roofer: 4.0
- painter: 3.5 (нижчий для демонстрації варіативності)
- hvac: 4.6
- painter2: 4.1

Коментарі:
```
"Дуже швидко прийшов, акуратно полагодив."
"Все зробив професійно, рекомендую."
"Чесно скажу — не дуже. Довелось викликати двічі."
"Чудова робота, дякую!"
"Прийшов вчасно, чистий після себе."
```

Після створення рейтингів викликаємо recompute reputation для кожного worker (probably post_save signal already does it, перевірити з бекенд-lead).

---

## 10. Reset — механіка

Ідея проста: щоденно о 23:00 за Києвом CronJob запускає `manage.py seed_demo --reset`, який scoped-видаляє все демо і сіє знову. Той самий command можна запустити вручну через `kubectl exec` для екстреного очищення (якщо клієнт зробив щось особливо неприйнятне посеред дня).

### 10.1 Django management command

```bash
python manage.py seed_demo \
    --reset \
    --passwords-from-env \
    --verbosity=1
```

Прапори:
- `--reset` — ПЕРЕД сіянням видаляє демо-скоуп (див. §11). Без прапора — ідемпотентне `update_or_create`.
- `--passwords-from-env` — тягне паролі з `DEMO_PASSWORD` env var (секрет у K8s). Без прапора — `Demo1234!` (тільки для dev).
- `--issues-count=N`, `--residents-count=N`, `--posts-count=N` — параметризація (для швидкого smoke у CI).
- `--dry-run` — тільки виводить що буде зроблено, нічого не чіпає. **Обов'язковий для першого запуску на проді** (sanity check: що саме буде видалено).

### 10.2 CronJob (нічний ресет)

Kubernetes 1.27+ підтримує `timeZone` у spec — використовуємо це, щоб забути про DST:

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: demo-reset-nightly
spec:
  schedule: "0 23 * * *"
  timeZone: "Europe/Kyiv"          # K8s ≥1.27
  concurrencyPolicy: Forbid        # якщо попередній ще не добіг — новий не стартує
  successfulJobsHistoryLimit: 3
  failedJobsHistoryLimit: 3
  jobTemplate:
    spec:
      backoffLimit: 1              # одна повторна спроба і все
      template:
        spec:
          restartPolicy: OnFailure
          containers:
          - name: reset
            image: apartmentos-backend:latest
            command: ["python", "manage.py", "seed_demo", "--reset", "--passwords-from-env"]
            env:
            - name: DJANGO_SETTINGS_MODULE
              value: "core.settings.production"
            - name: DEMO_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: demo-seed-secrets
                  key: DEMO_PASSWORD
```

**Чому 23:00 Києва**, а не 03:00 UTC:
- Продукт і клієнти — українські. 23:00 у нашій локалі = кінець робочого дня, клієнти вже не дивляться. О 23:05 демо готове і чисте до завтра.
- Якщо кластер у 1.26 чи старшому — `timeZone` не підтримується, тоді фіксуємо `"0 20 * * *"` (UTC літом, 21:00 UTC взимку) і оновлюємо двічі на рік вручну, або додаємо init-скрипт що конвертує. Краще апгрейднути K8s.

### 10.3 Ручний kill-switch

Якщо клієнт написав щось неприйнятне посеред дня і нічного ресету чекати не хочемо:

```bash
kubectl exec deployment/apartmentos-backend -- \
  python manage.py seed_demo --reset --passwords-from-env
```

Займає ~30 секунд, на час виконання демо тимчасово «пусте» (1-2 сек вікно між DELETE і INSERT у транзакції).

### 10.4 Deploy hook (опційно, не в MVP)

За бажанням продукту — можна повісити `seed_demo --reset` на пост-деплой у GitHub Actions. **Не рекомендую у MVP**:
- Подвійна підстраховка зайва — нічний cron і так тримає демо чистим.
- Ризик: баг у seed'і блокує деплой справжнього багфіксу.
- Якщо все ж треба — повісити на `if: contains(github.event.head_commit.message, '[reset-demo]')` — opt-in, не по замовчуванню.

### 10.5 Idempotency check після ресету

Після `--reset` команда валідує (у `_validate()` оркестратора):
- `Building.objects.filter(slug="demo-zelenyi-kvartal").count() == 1`
- `Issue.objects.filter(apartment__entrance__building__slug="demo-zelenyi-kvartal").count() in range(40, 60)`
- `User.objects.filter(email__iendswith="@demo.com", is_superuser=False).count() >= 30`
- Важливо: перевіряємо, що `User.objects.filter(is_superuser=True).count()` **не змінилося** від pre-reset snapshot'у.

Якщо щось не сходиться — exit 1 + Sentry alert. Тиха помилка у seed-скрипті = місяць без помічення = клієнти бачать обрубки.

---

## 11. Scoped reset — безпекові запобіжники

Найкрихкіша частина плану. Помилка тут = знесли продакшенові дані. Тому робимо параноїдально.

### 11.1 Queryset видалення

```python
# _reset_demo_scope.py
from django.contrib.auth import get_user_model
from django.db import transaction
from buildings.models import Building

DEMO_EMAIL_DOMAIN = "@demo.com"
DEMO_BUILDING_SLUG = "demo-zelenyi-kvartal"

User = get_user_model()


def reset_demo_scope(*, dry_run: bool = False) -> dict:
    """
    Scoped delete of demo data. Safe to run on prod.
    Returns counts of deleted objects for verification.
    """
    # Pre-flight snapshot — якщо що-небудь піде не так, по ньому валідуємо після rollback.
    pre_superuser_count = User.objects.filter(is_superuser=True).count()
    pre_non_demo_user_count = User.objects.exclude(
        email__iendswith=DEMO_EMAIL_DOMAIN
    ).count()

    demo_users_qs = User.objects.filter(
        email__iendswith=DEMO_EMAIL_DOMAIN,
        is_superuser=False,       # HARD GUARD — superuser ніколи не видаляється
    )
    demo_building_qs = Building.objects.filter(slug=DEMO_BUILDING_SLUG)

    counts = {
        "users_to_delete": demo_users_qs.count(),
        "buildings_to_delete": demo_building_qs.count(),
    }

    if dry_run:
        counts["dry_run"] = True
        return counts

    with transaction.atomic():
        # Cascade через ForeignKey(on_delete=CASCADE) на Profile, Issue, Post,
        # VehiclePass, Rating, Reply, Bookmark — Django самостійно зноситиме дочірні.
        demo_users_qs.delete()
        demo_building_qs.delete()  # каскадить Entrances → Units → Announcements

        # Post-condition assertion — якщо false, транзакція відкатиться.
        post_superuser_count = User.objects.filter(is_superuser=True).count()
        post_non_demo_user_count = User.objects.exclude(
            email__iendswith=DEMO_EMAIL_DOMAIN
        ).count()

        assert post_superuser_count == pre_superuser_count, (
            f"SAFETY VIOLATION: superuser count changed "
            f"({pre_superuser_count} → {post_superuser_count}). Rolling back."
        )
        assert post_non_demo_user_count == pre_non_demo_user_count, (
            f"SAFETY VIOLATION: non-demo users affected "
            f"({pre_non_demo_user_count} → {post_non_demo_user_count}). Rolling back."
        )

    return counts
```

### 11.2 Юніт-тест, який спить спокійно

Створюємо у `apps/profiles/tests/test_reset_demo_scope.py`:

```python
def test_reset_demo_does_not_touch_real_users_or_superuser(db):
    # Arrange: real prod-like data
    real_user = User.objects.create_user(email="manager@customer.example", password="x")
    real_building = Building.objects.create(slug="real-jk", name="Реальний ЖК")
    superuser = User.objects.create_superuser(email="admin@apartmentos.example", password="x")

    # Demo data to be wiped
    demo_user = User.objects.create_user(email="dispatcher@demo.com", password="x")
    demo_building = Building.objects.create(slug="demo-zelenyi-kvartal", name="Демо")

    # Act
    reset_demo_scope()

    # Assert — real survives
    assert User.objects.filter(id=real_user.id).exists()
    assert Building.objects.filter(id=real_building.id).exists()
    assert User.objects.filter(id=superuser.id).exists()
    # Demo — gone
    assert not User.objects.filter(id=demo_user.id).exists()
    assert not Building.objects.filter(id=demo_building.id).exists()
```

**Цей тест блокуючий у CI** — без нього `seed_demo` на прод не деплоїмо.

### 11.3 Додаткові запобіжники

- **Prod dry-run** — перший тиждень після розгортання cron викликається з `--dry-run` + прапором `SEED_DEMO_ALLOW_DELETE=false` у env. Логи йдуть у Sentry, людина дивиться, що збирається знестись. Потім перемикаємо на реальний delete.
- **Email domain whitelist у коді** — `DEMO_EMAIL_DOMAIN` константа, не з env. Щоб ніхто випадково не перевизначив `@.` і не зніс усіх.
- **Building slug pinning тест** — `test_demo_building_slug_is_stable` у CI перевіряє, що константа `DEMO_BUILDING_SLUG` дорівнює саме `"demo-zelenyi-kvartal"`. Перейменування зловить reviewer.
- **Sentry alert on any reset failure** — CronJob має `failedJobsHistoryLimit: 3`, плюс sidecar exports job status у Prometheus → alertmanager → Slack.

### 11.4 Orphan Tags cleanup (дрібниця)

Tags у поточній моделі глобальні — вони не каскадяться з автора посту. Після `reset` старі теги демо-постів можуть лишитися як сироти, якщо ніхто їх не використовує.

Варіанти:
1. **Не чіпати** — 12 тегів це дрібниця, вплив нульовий.
2. **Cleanup у команді**: `Tag.objects.annotate(n=Count("posts")).filter(n=0).delete()` після reset.

Рекомендую (2) — нуль вартості коду, тримає БД чистою.

---

## 12. Файлова структура бекенда

```
apps/profiles/management/commands/
├── seed_demo.py                    # Orchestrator (entrypoint)
├── _reset_demo_scope.py            # §11 safe scoped delete
├── _seed_building.py               # §3
├── _seed_users.py                  # §4
├── _seed_issues.py                 # §5
├── _seed_posts.py                  # §6
├── _seed_announcements.py          # §7
├── _seed_passes.py                 # §8
├── _seed_ratings.py                # §9
└── _seed_helpers.py                # Faker config, name pools, utils
```

Новий Django app не потрібен — усе живе в існуючому `profiles`.

Кожен `_seed_*.py` має сигнатуру:
```python
def seed(*, reset: bool, count: int | None = None, logger) -> dict:
    """Returns {"created": N, "updated": M}."""
```

Оркестратор `seed_demo.py`:
```python
class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true")
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--passwords-from-env", action="store_true")
        parser.add_argument("--issues-count", type=int, default=45)
        parser.add_argument("--residents-count", type=int, default=32)
        parser.add_argument("--posts-count", type=int, default=18)

    @transaction.atomic
    def handle(self, *args, **opts):
        if opts["reset"]:
            result = reset_demo_scope(dry_run=opts["dry_run"])
            self.stdout.write(f"Reset: {result}")
            if opts["dry_run"]:
                return

        _seed_building.seed()
        _seed_users.seed(residents_count=opts["residents_count"],
                         passwords_from_env=opts["passwords_from_env"])
        _seed_issues.seed(count=opts["issues_count"])
        _seed_posts.seed(count=opts["posts_count"])
        _seed_announcements.seed()
        _seed_passes.seed()
        _seed_ratings.seed()

        self._validate()
        self.stdout.write(self.style.SUCCESS("Demo seeded."))
```

---

## 13. Faker + determinism — базовий шаблон

```python
# _seed_helpers.py
import random, hashlib, uuid
from faker import Faker
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

KYIV = ZoneInfo("Europe/Kyiv")
BASE_TIME = datetime(2026, 4, 1, 9, 0, tzinfo=KYIV)
RANDOM_SEED = 42

DEMO_EMAIL_DOMAIN = "@demo.com"
DEMO_BUILDING_SLUG = "demo-zelenyi-kvartal"


def init_random():
    random.seed(RANDOM_SEED)
    f = Faker(["uk_UA"])
    Faker.seed(RANDOM_SEED)
    return f


def det_uuid(namespace: str, natural_key: str) -> uuid.UUID:
    """Deterministic UUID from (namespace, natural_key) — idempotent IDs across reruns."""
    base = hashlib.sha1(f"{namespace}:{natural_key}".encode()).digest()[:16]
    return uuid.UUID(bytes=base, version=5)


def ua_car_plate() -> str:
    letters = "АВЕКМНОРСТУХ"   # cyrillic look-alikes, український стандарт
    return (
        "".join(random.choices(letters, k=2))
        + f"{random.randint(1000, 9999)}"
        + "".join(random.choices(letters, k=2))
    )


# Pools для красивих імен, де Faker недостатньо:
DISPATCHERS = [
    ("Тетяна", "Романенко"),
    ("Олег",   "Степаненко"),
]
GUARDS = [
    ("Микола", "Гвоздюк"),
    ("Андрій", "Лук'яненко"),
    ("Петро",  "Савчук"),
]
WORKERS = [
    ("Василь",  "Мельник",    "plumber"),
    ("Ігор",    "Кравченко",  "electrician"),
    ("Степан",  "Бойко",      "carpenter"),
    ("Петро",   "Коваленко",  "mason"),
    ("Сергій",  "Павленко",   "roofer"),
    ("Марія",   "Іваницька",  "painter"),
    ("Валерій", "Середа",     "hvac"),
    ("Наталія", "Борисюк",    "painter"),
]
```

---

## 14. Тестування seed_demo

Три рівні:

1. **Unit tests (`apps/profiles/tests/test_seed_demo.py`)**: для кожного `_seed_*` модуля — тест що він створює правильну кількість, має правильні FK, ідемпотентний при повторному запуску.

2. **Safety test (`test_reset_demo_scope.py`, див. §11.2)** — real_user + superuser + demo_user, виконати reset, перевірити що real_user і superuser живі, demo_user зник. **Блокуючий у CI.**

3. **Integration test**: запуск повної команди `seed_demo --reset` у фікстурній БД → перевірка агрегатів (скільки Issue per status, per priority, що `/issues/` API повертає ≥40 результатів, і що `/profiles/admin/all/` не падає 500).

4. **E2E smoke**: у `sckandi-e2e/tests/smoke/demo-data.spec.ts` — один тест, що логіниться директором (dispatcher@demo.com), йде у `/admin/issues`, бачить ≥40 рядків у таблиці + варіативність статусів у колонці. Запускається у CI після деплою.

---

## 15. Rollout план

Реалістично — 1 спринт (2 тижні) без буферу, 3 тижні з буфером.

### Тиждень 1: Implementation
- `_reset_demo_scope.py` + safety тест (першим! блокуючий у CI).
- 8 seed-модулів (building, users, issues, posts, announcements, passes, ratings, helpers).
- Оркестратор `seed_demo.py` з усіма прапорами.
- Юніт-тести на кожен модуль + integration тест повної команди.
- Верифікувати що ідемпотентність реально працює: `seed_demo && seed_demo` → нуль дублікатів.

### Тиждень 2: CI/CD + staging burn-in
- Додати CronJob YAML у helm chart / manifests.
- Деплой на staging, cron запускається щодоби о 23:00 Kyiv — спостерігаємо тиждень.
- `--dry-run` у перші 3 запуски, потім реальний delete.
- Моніторимо: Sentry (0 помилок), Prometheus (job duration < 60s), Slack alerts, чи красиво виглядає демка вранці.

### Тиждень 3 (буфер / promote)
- Переносимо на prod тим же patchset'ом.
- Оновлюємо e2e suite — видаляємо workaround (див. §18).
- Sales team отримує інструкцію + credentials template.

---

## 16. Як потім видалити демо (якщо бізнес передумає)

Демо спроектовано так, щоб видалення було трьома командами:
```bash
kubectl delete cronjob demo-reset-nightly
kubectl exec deployment/apartmentos-backend -- \
    python manage.py shell -c "
from apps.profiles.management.commands._reset_demo_scope import reset_demo_scope
print(reset_demo_scope())
"
# видалити код seed_demo з репо (окремий PR)
```

Завдяки scoped-фільтрам (`@demo.com` + slug) і `on_delete=CASCADE` на існуючих FK, видалення зачищає все без сиріт, не чіпаючи реальних даних.

---

## 17. Відкриті питання (для product + backend lead)

1. **Чи роздавати worker-креди клієнтам?** Рекомендую **так** (як мінімум plumber@demo.com) — тоді клієнт побачить flow призначення з обох боків. Якщо ні — worker-акаунти лишаються як декорація.
2. **Чи дозволяти резидентам створювати нові заявки/пости на демо?** Рекомендую **так** (без rate-limit у MVP) — інакше клієнт не побачить живого функціоналу. Нічний ресет = страхувальна сітка.
3. **Рекламна кнопка у банері демо-режиму?** Наприклад «Сподобалось? → sales@...». Це **клієнтська, а не бекенд робота** — окремий тікет на front-end, якщо продукт скаже «так». У MVP — без банера взагалі: ми не показуємо його, бо клієнт і так знає що це демо (ми самі йому видали креди з попередженням).
4. **Локалізація?** Поки тільки українська. Англ — v2.
5. **Email-посилання у демо** — якщо наш продукт колись засилає клієнтам email (reset password, notifications), треба DISABLE SMTP у demo-контексті або підмінити на `localhost`/MailHog, щоб демо-юзер `tenant@demo.com` не отримував реальних листів на домен якого не існує.
6. **Rate limit** — без у MVP. Додаємо якщо Sentry покаже зловживання (клієнти ботами спамлять демо). Легко повісити `UserRateThrottle` на view'ах з перевіркою `user.email.endswith("@demo.com")`.

---

## 18. Зв'язок з e2e-тестами

Поточний `sckandi-e2e/fixtures/global-setup.ts` робить self-seeding як workaround — додає 4 Issue через API, якщо їх нема. **Після імплементації цього плану workaround стає непотрібним:**

1. Видалити `ensureIssuesSeeded` і `ensureTenantApartment` з `global-setup.ts`.
2. Видалити health-guard `authTest.skip()` у:
   - `admin-create-resident.spec.ts`
   - `access-control.spec.ts`
   - `admin-issue-status.spec.ts`
   - `assign-issue-flow.spec.ts`
3. Замінити `make seed` → `make seed-demo` у README e2e.

Це буде чистий `make e2e-full` без жодних «скіпнутих бекендних регресій».

---

## 19. Оцінка зусиль

Без Organization моделі це значно менше роботи, ніж у попередній чернетці.

| Етап | Back-end | DevOps | Front-end | Estimation |
|---|---|---|---|---|
| `_reset_demo_scope` + safety тест | 1 день | — | — | Робимо першим, окремо мерджимо |
| 8 seed-модулів (building, users, issues, posts, announcements, passes, ratings, helpers) | 3 дні | — | — | — |
| Оркестратор + CLI прапори + validation | 0.5 дні | — | — | — |
| Unit + integration тести | 1.5 дні | — | — | — |
| CronJob YAML + secrets + monitoring | — | 1 день | — | — |
| Staging burn-in (пасивне спостереження) | — | 0.5 дні | — | 7 днів wall-clock |
| Prod rollout + документація для sales | 0.5 дні | 0.5 дні | — | — |
| **Разом** | **~6.5 днів** | **~2 дні** | **0** | **1 спринт (2 тижні) з буфером** |

Front-end зміни = 0 у MVP (банер опційний, не блокує реліз).

---

## 20. Acceptance criteria

План вважається реалізованим, коли:

- [ ] `python manage.py seed_demo --reset` завершується з exit 0 на чистій БД.
- [ ] Після нього `GET /api/v1/issues/` повертає count ≥ 40.
- [ ] `GET /api/v1/profiles/admin/all/` повертає count ≥ 30 і status 200 (жодних 500!).
- [ ] `GET /api/v1/profiles/user/my-profile/` для всіх seeded users повертає 200.
- [ ] Admin UI `/admin/issues` показує таблицю з пагінацією, різними статусами, пріоритетами, assignee.
- [ ] Resident UI профіль показує ≥1 заявку, ≥1 перепустку, ≥1 пост у закладках.
- [ ] Guard UI показує ≥3 pending passes + історію closed.
- [ ] **Safety тест `test_reset_demo_does_not_touch_real_users_or_superuser` зелений у CI** — без нього не деплоїмо.
- [ ] CronJob `demo-reset-nightly` запускається щодоби о 23:00 Europe/Kyiv і відновлює чистий стан за ≤60 секунд.
- [ ] Sentry не бачить 500 помилок з `@demo.com` юзерів за 24h після деплою.
- [ ] Superuser-акаунт не змінюється після reset (перевіряється post-condition assertion у транзакції).
- [ ] Sales team має готовий credentials template у Notion / Slack.
- [ ] Всі 141 e2e тестів у `sckandi-e2e` проходять з нуля без health-guard skip'ів після увімкнення seed_demo у CI pipeline.

---

**Наступний крок:** невеликий ADR «Scoped demo reset via email-domain + building-slug markers» через `engineering:architecture` скіл — щоб formally зафіксувати рішення «без Organization моделі у MVP» і пояснити майбутнім інженерам, за яких умов цю обіцянку треба переглянути (наприклад, перший реальний мульти-тенант клієнт). Після мерджу ADR — запускаємо Тиждень 1 з §15.
