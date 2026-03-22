"""Demo seed command: creates a realistic ОСББ/building dataset."""
import random
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

User = get_user_model()


class Command(BaseCommand):
    help = "Seed demo data: 1 building, 2 entrances, 20 units, users, requests, announcements"

    def handle(self, *args, **options):
        from apps.apartments.models import Apartment, Building, Entrance, Unit
        from apps.issues.models import Category, Issue
        from apps.posts.models import Announcement

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

        # ── 4. Dispatcher / Admin user ───────────────────────────────────
        dispatcher, created = User.objects.get_or_create(
            email="dispatcher@demo.com",
            defaults={
                "username": "dispatcher",
                "first_name": "Олена",
                "last_name": "Коваль",
                "is_staff": True,
                "is_active": True,
            },
        )
        if created:
            dispatcher.set_password("Demo1234!")
            dispatcher.save()
            self.stdout.write(f"  ✓ Dispatcher: {dispatcher.email} / Demo1234!")

        # ── 4b. Guard user ───────────────────────────────────────────────
        from apps.profiles.models import Profile

        guard, created = User.objects.get_or_create(
            email="guard@demo.com",
            defaults={
                "username": "guard",
                "first_name": "Микола",
                "last_name": "Охоронець",
                "is_active": True,
            },
        )
        if created:
            guard.set_password("Demo1234!")
            guard.save()
        Profile.objects.filter(user=guard).update(occupation=Profile.Occupation.GUARD)
        self.stdout.write(f"  ✓ Guard: {guard.email} / Demo1234!")

        # ── 4c. Test tenant user ─────────────────────────────────────────
        tenant_user, created = User.objects.get_or_create(
            email="tenant@demo.com",
            defaults={
                "username": "tenant",
                "first_name": "Іван",
                "last_name": "Тестовий",
                "is_active": True,
            },
        )
        if created:
            tenant_user.set_password("Demo1234!")
            tenant_user.save()
        Profile.objects.filter(user=tenant_user).update(occupation=Profile.Occupation.TENANT)
        self.stdout.write(f"  ✓ Tenant: {tenant_user.email} / Demo1234!")

        # ── 5. Resident users (3) linked to units ────────────────────────
        residents_data = [
            ("resident1@demo.com", "Іван", "Петренко", "resident1", units[0]),
            ("resident2@demo.com", "Марія", "Шевченко", "resident2", units[2]),
            ("resident3@demo.com", "Андрій", "Бондаренко", "resident3", units[4]),
        ]
        residents = []
        for email, first, last, username, unit in residents_data:
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    "username": username,
                    "first_name": first,
                    "last_name": last,
                    "is_active": True,
                },
            )
            if created:
                user.set_password("Demo1234!")
                user.save()

            # Link via Apartment (legacy model as bridge)
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

            # Link Unit → Apartment
            if not unit.apartment:
                unit.apartment = apt
                unit.save()

            residents.append((user, unit, apt))
            self.stdout.write(f"  ✓ Resident: {email} / Demo1234! (Unit {unit.number})")

        # ── 6. Categories ────────────────────────────────────────────────
        categories = []
        for name, sla in [
            ("Сантехніка", 24),
            ("Електрика", 48),
            ("Загальні приміщення", 72),
            ("Ліфт", 8),
        ]:
            cat, _ = Category.objects.get_or_create(name=name, defaults={"sla_hours": sla})
            categories.append(cat)

        # ── 7. Service requests (10 with mixed statuses) ─────────────────
        statuses = ["reported", "accepted", "in_progress", "done", "rejected"]
        issue_data = [
            ("Протікає труба у ванній", "Сантехніка"),
            ("Не працює розетка в кухні", "Електрика"),
            ("Зламався ліфт", "Ліфт"),
            ("Брудно в під'їзді", "Загальні приміщення"),
            ("Немає гарячої води", "Сантехніка"),
            ("Перегоріла лампа в коридорі", "Електрика"),
            ("Ліфт шумить", "Ліфт"),
            ("Зламані поштові скриньки", "Загальні приміщення"),
            ("Засмічена каналізація", "Сантехніка"),
            ("Поганий запах у підвалі", "Загальні приміщення"),
        ]
        cat_map = {c.name: c for c in categories}
        for i, (title, cat_name) in enumerate(issue_data):
            user, unit, apt = residents[i % len(residents)]
            cat = cat_map[cat_name]
            status = statuses[i % len(statuses)]
            due = timezone.now() + timedelta(hours=cat.sla_hours) - timedelta(hours=random.randint(0, 96))
            issue, created = Issue.objects.get_or_create(
                title=title,
                reported_by=user,
                defaults={
                    "apartment": apt,
                    "unit": unit,
                    "category": cat,
                    "description": f"Опис проблеми: {title}",
                    "status": status,
                    "priority": ["low", "medium", "high"][i % 3],
                    "due_at": due,
                },
            )
            if created and status in ("done", "resolved"):
                issue.resolved_on = timezone.now().date()
                issue.save()

        self.stdout.write(f"  ✓ Created/verified 10 service requests")

        # ── 8. Announcements (8) ─────────────────────────────────────────
        announcements_data = [
            ("Планове відключення води", "27 березня 2026 з 09:00 до 18:00 буде відключена холодна вода у зв'язку з ремонтом мережі. Просимо завчасно запастися водою."),
            ("Прибирання двору", "Щосуботи о 10:00 спільне прибирання прибудинкової території. Запрошуємо всіх мешканців! Інвентар надається."),
            ("Перевірка ліфтів", "30 березня технічна перевірка ліфтів. Можливі короткочасні зупинки з 10:00 до 13:00."),
            ("Нові правила паркування", "З 1 квітня вводяться нові правила паркування на прибудинковій території. Детальніше в оголошенні на дошці біля входу."),
            ("Збори ОСББ", "5 квітня о 18:00 чергові збори мешканців. Порядок денний: звіт голови, питання ремонту даху."),
            ("🎉 Відкриття дитячого майданчика!", "Раді повідомити, що 15 квітня о 12:00 відбудеться урочисте відкриття нового дитячого майданчика у дворі ЖК Сонячний. Встановлено гірки, гойдалки, пісочницю та лавки для батьків. Запрошуємо всіх мешканців з дітьми!"),
            ("Озеленення прибудинкової території", "У травні розпочинаємо висадку дерев та квітів на прибудинковій території. Якщо бажаєте долучитися — звертайтесь до управителя."),
            ("Встановлення відеоспостереження", "Повідомляємо, що до кінця квітня буде встановлено 8 камер відеоспостереження на входах і паркінгу. Це підвищить безпеку нашого ЖК."),
        ]
        for title, body in announcements_data:
            Announcement.objects.get_or_create(
                building=building,
                title=title,
                defaults={"body": body, "is_active": True},
            )
        self.stdout.write(f"  ✓ Created/verified {len(announcements_data)} announcements")

        # ── 9. News articles (6) ───────────────────────────────────────
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

        news_data = [
            {
                "title": "Запуск нового порталу Skandi Apartments",
                "excerpt": "Раді представити оновлений портал для мешканців ЖК Сонячний з новими можливостями.",
                "body": "Шановні мешканці! Ми раді повідомити про запуск нового порталу управління Skandi Apartments. "
                        "Тепер ви можете подавати заявки на обслуговування, отримувати оголошення та керувати перепустками онлайн.",
                "category": cat_info,
                "pinned": True,
            },
            {
                "title": "Графік прибирання на березень 2026",
                "excerpt": "Оновлений графік прибирання спільних приміщень та прибудинкової території.",
                "body": "Прибирання під'їздів: щодня з 08:00 до 10:00. Прибирання двору: понеділок, середа, п'ятниця. "
                        "Миття вікон на сходових клітках: перша субота місяця.",
                "category": cat_maintenance,
                "pinned": False,
            },
            {
                "title": "День відкритих дверей в ЖК Сонячний",
                "excerpt": "Запрошуємо на екскурсію по оновлених спільних приміщеннях 5 квітня.",
                "body": "5 квітня о 14:00 відбудеться день відкритих дверей. Ви зможете оглянути оновлений спортзал, "
                        "коворкінг та дитячу кімнату. Реєстрація на порталі.",
                "category": cat_events,
                "pinned": False,
            },
            {
                "title": "Нові тарифи на обслуговування з 1 квітня",
                "excerpt": "Інформація про зміни в тарифах на комунальні послуги.",
                "body": "З 1 квітня 2026 року змінюються тарифи на утримання будинку та прибудинкової території. "
                        "Детальна інформація доступна у розділі документів.",
                "category": cat_info,
                "pinned": False,
            },
            {
                "title": "Встановлення нових поштових скриньок",
                "excerpt": "Цього тижня буде завершено заміну поштових скриньок у обох під'їздах.",
                "body": "Нові антивандальні поштові скриньки з індивідуальними ключами будуть встановлені до кінця тижня. "
                        "Ключі можна отримати у консьєржа.",
                "category": cat_maintenance,
                "pinned": False,
            },
            {
                "title": "Результати зборів ОСББ від 15 березня",
                "excerpt": "Підсумки чергових зборів мешканців та прийняті рішення.",
                "body": "На зборах було прийнято рішення про ремонт даху, оновлення ліфтів та встановлення зарядних станцій "
                        "для електромобілів. Повний протокол доступний на порталі.",
                "category": cat_events,
                "pinned": False,
            },
        ]

        now = timezone.now()
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

        self.stdout.write(self.style.SUCCESS(
            "\n✅ Demo seed complete!\n"
            f"   Building: {building.name}\n"
            f"   Entrances: 2, Units: {Unit.objects.count()}\n"
            f"   Issues: {Issue.objects.count()}\n"
            f"   Announcements: {Announcement.objects.count()} (включно з відкриттям майданчика)\n"
            "\n   Login credentials:\n"
            "   dispatcher@demo.com / Demo1234! (staff)\n"
            "   guard@demo.com / Demo1234! (guard)\n"
            "   tenant@demo.com / Demo1234! (tenant)\n"
            "   resident1@demo.com / Demo1234!\n"
            "   resident2@demo.com / Demo1234!\n"
            "   resident3@demo.com / Demo1234!\n"
        ))
