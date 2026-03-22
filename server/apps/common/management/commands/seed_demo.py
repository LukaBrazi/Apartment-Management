"""Demo seed command: creates a realistic ОСББ/building dataset."""
import random
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

User = get_user_model()


def _ensure_user(email, password="Demo1234!", **fields):
    """Create or update a user, always forcing is_active=True and resetting password."""
    user, created = User.objects.get_or_create(email=email, defaults=fields)
    # Always force active + correct password (handles re-seed after flush or manual edits)
    changed = False
    if not user.is_active:
        user.is_active = True
        changed = True
    for k, v in fields.items():
        if getattr(user, k, None) != v:
            setattr(user, k, v)
            changed = True
    user.set_password(password)
    user.save()
    return user, created


class Command(BaseCommand):
    help = "Seed demo data: buildings, users, requests, announcements, news, passes"

    def handle(self, *args, **options):
        from apps.apartments.models import Apartment, Building, Entrance, Unit
        from apps.issues.models import Category, Issue
        from apps.passes.models import VehiclePass
        from apps.posts.models import Announcement
        from apps.profiles.models import Profile

        now = timezone.now()
        self.stdout.write("🌱 Seeding demo data...")

        # ── 1. Building ──────────────────────────────────────────────────
        building, _ = Building.objects.get_or_create(
            name="ЖК Сонячний",
            defaults={
                "address": "вул. Хрещатик, 1",
                "city": "Kyiv",
                "is_active": True,
            },
        )

        # ── 2. Entrances ─────────────────────────────────────────────────
        entrance1, _ = Entrance.objects.get_or_create(building=building, name="1")
        entrance2, _ = Entrance.objects.get_or_create(building=building, name="2")

        # ── 3. Units (20 total: 10 per entrance, floors 1-5) ─────────────
        units = []
        for floor in range(1, 6):
            for pos in range(1, 3):
                unit_num = str((floor - 1) * 2 + pos)
                unit, _ = Unit.objects.get_or_create(
                    entrance=entrance1,
                    number=unit_num,
                    defaults={"floor": floor},
                )
                units.append(unit)
        for floor in range(1, 6):
            for pos in range(1, 3):
                unit_num = str(100 + (floor - 1) * 2 + pos)
                unit, _ = Unit.objects.get_or_create(
                    entrance=entrance2,
                    number=unit_num,
                    defaults={"floor": floor},
                )
                units.append(unit)

        # ── 4. Superuser (for Django admin) ───────────────────────────────
        admin, _ = _ensure_user(
            "admin@demo.com",
            username="admin",
            first_name="Адмін",
            last_name="Системний",
            is_staff=True,
            is_superuser=True,
        )
        self.stdout.write(f"  ✓ Superuser: admin@demo.com / Demo1234!")

        # ── 5. Staff users ────────────────────────────────────────────────
        dispatcher, _ = _ensure_user(
            "dispatcher@demo.com",
            username="dispatcher",
            first_name="Олена",
            last_name="Коваль",
            is_staff=True,
        )
        Profile.objects.filter(user=dispatcher).update(
            occupation=Profile.Occupation.ELECTRICIAN,
            gender=Profile.Gender.FEMALE,
            phone_number="+380501234567",
            country_of_origin="UA",
            city_of_origin="Київ",
            bio="Диспетчер ЖК Сонячний. Відповідаю за координацію робіт.",
        )
        self.stdout.write(f"  ✓ Dispatcher: {dispatcher.email} / Demo1234!")

        guard, _ = _ensure_user(
            "guard@demo.com",
            username="guard",
            first_name="Микола",
            last_name="Охоронець",
        )
        Profile.objects.filter(user=guard).update(
            occupation=Profile.Occupation.GUARD,
            gender=Profile.Gender.MALE,
            phone_number="+380509876543",
            country_of_origin="UA",
            city_of_origin="Київ",
            bio="Охоронець ЖК Сонячний. Цілодобова вахта.",
        )
        self.stdout.write(f"  ✓ Guard: {guard.email} / Demo1234!")

        # Plumber
        plumber, _ = _ensure_user(
            "plumber@demo.com",
            username="plumber",
            first_name="Петро",
            last_name="Сантехнік",
        )
        Profile.objects.filter(user=plumber).update(
            occupation=Profile.Occupation.PLUMBER,
            gender=Profile.Gender.MALE,
            phone_number="+380671112233",
            country_of_origin="UA",
            city_of_origin="Київ",
            bio="Сантехнік ЖК. Стаж 15 років.",
        )
        self.stdout.write(f"  ✓ Plumber: {plumber.email} / Demo1234!")

        # Electrician
        electrician, _ = _ensure_user(
            "electrician@demo.com",
            username="electrician",
            first_name="Сергій",
            last_name="Електрик",
        )
        Profile.objects.filter(user=electrician).update(
            occupation=Profile.Occupation.ELECTRICIAN,
            gender=Profile.Gender.MALE,
            phone_number="+380674445566",
            country_of_origin="UA",
            city_of_origin="Бровари",
            bio="Електрик ЖК. Обслуговування електромереж.",
        )
        self.stdout.write(f"  ✓ Electrician: {electrician.email} / Demo1234!")

        # ── 5. Tenant users (no apartment yet — for testing) ──────────────
        tenant_user, _ = _ensure_user(
            "tenant@demo.com",
            username="tenant",
            first_name="Іван",
            last_name="Тестовий",
        )
        Profile.objects.filter(user=tenant_user).update(
            occupation=Profile.Occupation.TENANT,
            gender=Profile.Gender.MALE,
            phone_number="+380637778899",
            country_of_origin="UA",
            city_of_origin="Київ",
        )
        self.stdout.write(f"  ✓ Tenant (no apartment): {tenant_user.email} / Demo1234!")

        # ── 6. Resident users linked to units ─────────────────────────────
        residents_data = [
            ("resident1@demo.com", "Іван", "Петренко", "resident1", units[0], Profile.Gender.MALE, "+380501110001"),
            ("resident2@demo.com", "Марія", "Шевченко", "resident2", units[2], Profile.Gender.FEMALE, "+380501110002"),
            ("resident3@demo.com", "Андрій", "Бондаренко", "resident3", units[4], Profile.Gender.MALE, "+380501110003"),
            ("resident4@demo.com", "Олена", "Мельник", "resident4", units[6], Profile.Gender.FEMALE, "+380501110004"),
            ("resident5@demo.com", "Дмитро", "Коваленко", "resident5", units[8], Profile.Gender.MALE, "+380501110005"),
            ("resident6@demo.com", "Наталія", "Литвиненко", "resident6", units[10], Profile.Gender.FEMALE, "+380501110006"),
            ("resident7@demo.com", "Олексій", "Мороз", "resident7", units[12], Profile.Gender.MALE, "+380501110007"),
            ("resident8@demo.com", "Тетяна", "Савченко", "resident8", units[14], Profile.Gender.FEMALE, "+380501110008"),
        ]
        residents = []
        for email, first, last, username, unit, gender, phone in residents_data:
            user, _ = _ensure_user(email, username=username, first_name=first, last_name=last)
            Profile.objects.filter(user=user).update(
                occupation=Profile.Occupation.TENANT,
                gender=gender,
                phone_number=phone,
                country_of_origin="UA",
                city_of_origin="Київ",
                unit=unit,
            )

            apt, _ = Apartment.objects.get_or_create(
                unit_number=unit.number,
                defaults={
                    "building": building.name,
                    "floor": unit.floor or 1,
                    "tenant": user,
                },
            )
            apt.tenant = user
            apt.save()
            if not unit.apartment:
                unit.apartment = apt
                unit.save()

            residents.append((user, unit, apt))
            self.stdout.write(f"  ✓ Resident: {email} / Demo1234! (Unit {unit.number})")

        # ── 7. Categories ────────────────────────────────────────────────
        categories = []
        for name, sla in [
            ("Сантехніка", 24),
            ("Електрика", 48),
            ("Загальні приміщення", 72),
            ("Ліфт", 8),
            ("Опалення", 24),
            ("Вентиляція", 48),
        ]:
            cat, _ = Category.objects.get_or_create(name=name, defaults={"sla_hours": sla})
            categories.append(cat)

        # ── 8. Service requests (15 with mixed statuses) ──────────────────
        statuses = ["reported", "accepted", "in_progress", "done", "rejected"]
        issue_data = [
            ("Протікає труба у ванній", "Сантехніка", "Труба під раковиною протікає вже два дні. Вода збирається на підлозі."),
            ("Не працює розетка в кухні", "Електрика", "Розетка біля холодильника перестала працювати. Інші розетки в кухні працюють."),
            ("Зламався ліфт", "Ліфт", "Ліфт зупинився між 3 та 4 поверхами. Зараз двері не відчиняються."),
            ("Брудно в під'їзді", "Загальні приміщення", "На 2 поверсі під'їзду 1 вже тиждень не прибирали. Є сміття та пил."),
            ("Немає гарячої води", "Сантехніка", "З ранку немає гарячої води в квартирі. Холодна йде нормально."),
            ("Перегоріла лампа в коридорі", "Електрика", "На 4 поверсі перегоріла лампа в коридорі. Дуже темно ввечері."),
            ("Ліфт шумить", "Ліфт", "При русі ліфта чутно металевий скрегіт. Потрібна перевірка."),
            ("Зламані поштові скриньки", "Загальні приміщення", "Декілька поштових скриньок в під'їзді 2 зламані, дверцята не закриваються."),
            ("Засмічена каналізація", "Сантехніка", "Каналізація в ванній забита. Вода стоїть і не зливається."),
            ("Поганий запах у підвалі", "Загальні приміщення", "З підвалу йде неприємний запах. Можливо прорив каналізації."),
            ("Не працює опалення", "Опалення", "Батарея в спальні холодна, хоча в інших кімнатах працює."),
            ("Шум у вентиляції", "Вентиляція", "Вентиляційна шахта вібрує і створює сильний шум, особливо вночі."),
            ("Тріщина в стіні під'їзду", "Загальні приміщення", "Помітна тріщина на стіні між 3 та 4 поверхом. Зростає з часом."),
            ("Протікає дах над 5 поверхом", "Сантехніка", "Після дощу з'являються плями на стелі квартири на 5 поверсі."),
            ("Не працює домофон", "Електрика", "Домофон на вході під'їзду 1 не реагує на натискання кнопок."),
        ]
        cat_map = {c.name: c for c in categories}
        for i, (title, cat_name, description) in enumerate(issue_data):
            user, unit, apt = residents[i % len(residents)]
            cat = cat_map[cat_name]
            status = statuses[i % len(statuses)]
            due = now + timedelta(hours=cat.sla_hours) - timedelta(hours=random.randint(0, 96))
            issue, created = Issue.objects.get_or_create(
                title=title,
                reported_by=user,
                defaults={
                    "apartment": apt,
                    "unit": unit,
                    "category": cat,
                    "description": description,
                    "status": status,
                    "priority": ["low", "medium", "high"][i % 3],
                    "due_at": due,
                },
            )
            if created and status in ("done", "resolved"):
                issue.resolved_on = now.date()
                issue.save()

        self.stdout.write(f"  ✓ Created/verified {len(issue_data)} service requests")

        # ── 9. Announcements (10) ────────────────────────────────────────
        announcements_data = [
            ("Планове відключення води", "27 березня 2026 з 09:00 до 18:00 буде відключена холодна вода у зв'язку з ремонтом мережі. Просимо завчасно запастися водою."),
            ("Прибирання двору", "Щосуботи о 10:00 спільне прибирання прибудинкової території. Запрошуємо всіх мешканців! Інвентар надається."),
            ("Перевірка ліфтів", "30 березня технічна перевірка ліфтів. Можливі короткочасні зупинки з 10:00 до 13:00."),
            ("Нові правила паркування", "З 1 квітня вводяться нові правила паркування на прибудинковій території. Детальніше в оголошенні на дошці біля входу."),
            ("Збори ОСББ", "5 квітня о 18:00 чергові збори мешканців. Порядок денний: звіт голови, питання ремонту даху."),
            ("🎉 Відкриття дитячого майданчика!", "Раді повідомити, що 15 квітня о 12:00 відбудеться урочисте відкриття нового дитячого майданчика у дворі ЖК Сонячний. Встановлено гірки, гойдалки, пісочницю та лавки для батьків."),
            ("Озеленення прибудинкової території", "У травні розпочинаємо висадку дерев та квітів на прибудинковій території. Якщо бажаєте долучитися — звертайтесь до управителя."),
            ("Встановлення відеоспостереження", "Повідомляємо, що до кінця квітня буде встановлено 8 камер відеоспостереження на входах і паркінгу. Це підвищить безпеку нашого ЖК."),
            ("Заміна лічильників води", "З 1 по 15 квітня відбудеться планова заміна лічильників холодної та гарячої води. Графік за квартирами буде розміщено на дошці оголошень."),
            ("Ремонт дахового покриття", "З 20 квітня розпочинається капітальний ремонт дахового покриття. Роботи триватимуть орієнтовно 3 тижні. Просимо вибачення за можливі незручності."),
        ]
        for title, body in announcements_data:
            Announcement.objects.get_or_create(
                building=building,
                title=title,
                defaults={"body": body, "is_active": True},
            )
        self.stdout.write(f"  ✓ Created/verified {len(announcements_data)} announcements")

        # ── 10. News articles (8) ─────────────────────────────────────────
        from apps.news.models import News, NewsCategory

        cat_info, _ = NewsCategory.objects.get_or_create(
            name="Інформація", defaults={"color": "#4A90D9"}
        )
        cat_events, _ = NewsCategory.objects.get_or_create(
            name="Події", defaults={"color": "#2D8A4E"}
        )
        cat_maintenance, _ = NewsCategory.objects.get_or_create(
            name="Обслуговування", defaults={"color": "#D97706"}
        )
        cat_safety, _ = NewsCategory.objects.get_or_create(
            name="Безпека", defaults={"color": "#DC2626"}
        )

        news_data = [
            {
                "title": "Запуск нового порталу Skandi Apartments",
                "excerpt": "Раді представити оновлений портал для мешканців ЖК Сонячний з новими можливостями.",
                "body": "Шановні мешканці! Ми раді повідомити про запуск нового порталу управління Skandi Apartments. "
                        "Тепер ви можете подавати заявки на обслуговування, отримувати оголошення та керувати перепустками онлайн. "
                        "Портал доступний за адресою http://localhost:8080 та працює цілодобово.",
                "category": cat_info,
                "pinned": True,
            },
            {
                "title": "Графік прибирання на березень 2026",
                "excerpt": "Оновлений графік прибирання спільних приміщень та прибудинкової території.",
                "body": "Прибирання під'їздів: щодня з 08:00 до 10:00. Прибирання двору: понеділок, середа, п'ятниця. "
                        "Миття вікон на сходових клітках: перша субота місяця. Графік діє з 1 березня по 31 березня 2026 року.",
                "category": cat_maintenance,
                "pinned": False,
            },
            {
                "title": "День відкритих дверей в ЖК Сонячний",
                "excerpt": "Запрошуємо на екскурсію по оновлених спільних приміщеннях 5 квітня.",
                "body": "5 квітня о 14:00 відбудеться день відкритих дверей. Ви зможете оглянути оновлений спортзал, "
                        "коворкінг та дитячу кімнату. Реєстрація на порталі. Для мешканців та гостей.",
                "category": cat_events,
                "pinned": False,
            },
            {
                "title": "Нові тарифи на обслуговування з 1 квітня",
                "excerpt": "Інформація про зміни в тарифах на комунальні послуги.",
                "body": "З 1 квітня 2026 року змінюються тарифи на утримання будинку та прибудинкової території. "
                        "Детальна інформація доступна у розділі документів порталу та на дошці оголошень.",
                "category": cat_info,
                "pinned": False,
            },
            {
                "title": "Встановлення нових поштових скриньок",
                "excerpt": "Цього тижня буде завершено заміну поштових скриньок у обох під'їздах.",
                "body": "Нові антивандальні поштові скриньки з індивідуальними ключами будуть встановлені до кінця тижня. "
                        "Ключі можна отримати у консьєржа з понеділка по п'ятницю з 09:00 до 18:00.",
                "category": cat_maintenance,
                "pinned": False,
            },
            {
                "title": "Результати зборів ОСББ від 15 березня",
                "excerpt": "Підсумки чергових зборів мешканців та прийняті рішення.",
                "body": "На зборах було прийнято рішення про ремонт даху, оновлення ліфтів та встановлення зарядних станцій "
                        "для електромобілів. Повний протокол доступний на порталі у розділі документів.",
                "category": cat_events,
                "pinned": False,
            },
            {
                "title": "Перевірка систем пожежної безпеки",
                "excerpt": "25 березня відбудеться планова перевірка систем пожежної сигналізації та пожежогасіння.",
                "body": "Просимо мешканців забезпечити доступ до пожежних щитків та гідрантів на поверхах. "
                        "Перевірка триватиме з 10:00 до 16:00. Можливі короткочасні спрацювання сигналізації.",
                "category": cat_safety,
                "pinned": False,
            },
            {
                "title": "Онлайн-оплата комунальних послуг",
                "excerpt": "Тепер можна оплачувати комунальні послуги через портал Skandi Apartments.",
                "body": "Ми інтегрували систему онлайн-оплати з основними банками України. Тепер ви можете переглядати "
                        "нарахування та сплачувати комунальні послуги прямо через особистий кабінет на порталі.",
                "category": cat_info,
                "pinned": True,
            },
        ]

        for i, nd in enumerate(news_data):
            News.objects.get_or_create(
                title=nd["title"],
                defaults={
                    "excerpt": nd["excerpt"],
                    "body": nd["body"],
                    "category": nd["category"],
                    "author": dispatcher,
                    "is_published": True,
                    "published_at": now - timedelta(days=len(news_data) - i),
                    "pinned": nd["pinned"],
                },
            )
        self.stdout.write(f"  ✓ Created/verified {len(news_data)} news articles")

        # ── 11. Vehicle passes (12) ───────────────────────────────────────
        pass_data = [
            ("АА1234ВВ", "Приїде друг на вихідні", 1),
            ("ВН5678КА", "Доставка меблів з IKEA", 0),
            ("АІ9012НР", "Таксі на аеропорт", -1),
            ("СА3456ОЕ", "Вантажівка для переїзду", 2),
            ("АА7890ТТ", "Гості на день народження", 3),
            ("ВС1111КК", "Кур'єр Нова Пошта", 0),
            ("АА2222НН", "Сантехнік з виклику", -2),
            ("КА3333ОО", "Батьки приїдуть з Львова", 4),
            ("ВН4444РР", "Евакуатор для авто", -1),
            ("АА5555СС", "Доставка продуктів Glovo", 0),
            ("ТТ6666ВВ", "Бригада електриків", 1),
            ("АА7777ММ", "Рієлтор на огляд квартири", 2),
        ]
        for i, (car, comment, day_offset) in enumerate(pass_data):
            user, unit, apt = residents[i % len(residents)]
            visit = now.date() + timedelta(days=day_offset)
            status = VehiclePass.Status.CLOSED if day_offset < 0 else VehiclePass.Status.PENDING
            vp, created = VehiclePass.objects.get_or_create(
                tenant=user,
                car_number=car,
                visit_date=visit,
                defaults={
                    "unit": unit,
                    "comment": comment,
                    "status": status,
                },
            )
            if created and status == VehiclePass.Status.CLOSED:
                vp.closed_by = guard
                vp.closed_at = now - timedelta(hours=random.randint(1, 48))
                vp.save()

        self.stdout.write(f"  ✓ Created/verified {len(pass_data)} vehicle passes")

        # ── 12. Summary ──────────────────────────────────────────────────
        self.stdout.write(self.style.SUCCESS(
            "\n✅ Demo seed complete!\n"
            f"   Building: {building.name}\n"
            f"   Entrances: 2, Units: {Unit.objects.count()}\n"
            f"   Users: {User.objects.count()}\n"
            f"   Issues: {Issue.objects.count()}\n"
            f"   Announcements: {Announcement.objects.count()}\n"
            f"   News: {News.objects.filter(is_published=True).count()}\n"
            f"   Vehicle Passes: {VehiclePass.objects.count()}\n"
            "\n   Login credentials (all passwords: Demo1234!):\n"
            "   ──────────────────────────────────────────\n"
            "   dispatcher@demo.com  (staff/диспетчер)\n"
            "   guard@demo.com       (охоронець)\n"
            "   plumber@demo.com     (сантехнік)\n"
            "   electrician@demo.com (електрик)\n"
            "   tenant@demo.com      (мешканець без квартири)\n"
            "   resident1@demo.com   (мешканець, кв. 1)\n"
            "   resident2@demo.com   (мешканець, кв. 3)\n"
            "   resident3@demo.com   (мешканець, кв. 5)\n"
            "   resident4@demo.com   (мешканець, кв. 7)\n"
            "   resident5@demo.com   (мешканець, кв. 9)\n"
            "   resident6@demo.com   (мешканець, кв. 101)\n"
            "   resident7@demo.com   (мешканець, кв. 103)\n"
            "   resident8@demo.com   (мешканець, кв. 105)\n"
        ))
