"""Demo seed command: creates a realistic ОСББ/building dataset for ЖК Скандинавія."""
import random
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import IntegrityError, transaction
from django.utils import timezone

User = get_user_model()


def _ensure_user(email, password="Demo1234!", **fields):
    """Create or update a user, always forcing is_active=True and resetting password."""
    user, created = User.objects.get_or_create(email=email, defaults=fields)
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


def _link_unit_apartment(unit, apt):
    """Link apt → unit via OneToOne only if not already linked (idempotent)."""
    unit.refresh_from_db()
    if unit.apartment_id == apt.pk:
        return
    if unit.apartment_id is not None:
        return
    with transaction.atomic():
        try:
            unit.apartment = apt
            unit.save(update_fields=["apartment"])
        except IntegrityError:
            pass


class Command(BaseCommand):
    help = "Seed demo data: ЖК Скандинавія — buildings, users, issues, news, passes"

    def handle(self, *args, **options):
        from apps.apartments.models import Apartment, Building, Entrance, ResidentialComplex, Unit
        from apps.issues.models import Category, Issue
        from apps.passes.models import VehiclePass
        from apps.posts.models import Announcement, Post
        from apps.profiles.models import Profile
        from apps.site_settings.models import SiteSettings, ContactPerson
        from apps.organizations.models import Organization, OrganizationMembership, OrgRole, OrganizationType

        now = timezone.now()
        self.stdout.write("🌿 Seeding ЖК Скандинавія demo data...")

        # ── 0. Residential Complex ────────────────────────────────────────
        complex_obj, _ = ResidentialComplex.objects.get_or_create(
            name="ЖК Скандинавія",
            defaults={
                "address": "просп. Берестейський, 40-В, Київ",
                "city": "Київ",
                "description": (
                    "Преміальний житловий комплекс ЖК Скандинавія у Святошинському районі Києва. "
                    "3 будинки у скандинавському стилі, підземний паркінг, дитячий садок, фітнес-центр. "
                    "Власна котельня, 24/7 охорона, консьєрж-сервіс."
                ),
            },
        )

        # ── 0.1. Organization (for multi-tenant setup) ────────────────────
        demo_org, _ = Organization.objects.get_or_create(
            slug="skandinaviya-demo",
            defaults={
                "name": "ЖК Скандинавія (Demo)",
                "type": OrganizationType.HOUSING_COMPLEX,
                "is_active": True,
                "features": {"issues": True, "passes": True, "news": True, "ratings": True},
            },
        )
        self.stdout.write(f"  ✓ Organization: {demo_org.name}")

        site = SiteSettings.get()
        if not site.current_complex:
            site.current_complex = complex_obj
            site.save()
        self.stdout.write(f"  ✓ Residential Complex: {complex_obj.name}")

        # ── 1. Buildings ──────────────────────────────────────────────────
        building_a, _ = Building.objects.get_or_create(
            name="Корпус А «Норд»",
            defaults={
                "address": "просп. Берестейський, 40-А",
                "city": "Київ",
                "is_active": True,
                "complex": complex_obj,
            },
        )
        if not building_a.complex:
            building_a.complex = complex_obj
            building_a.save()

        building_b, _ = Building.objects.get_or_create(
            name="Корпус Б «Вест»",
            defaults={
                "address": "просп. Берестейський, 40-Б",
                "city": "Київ",
                "is_active": True,
                "complex": complex_obj,
            },
        )
        if not building_b.complex:
            building_b.complex = complex_obj
            building_b.save()

        building_c, _ = Building.objects.get_or_create(
            name="Корпус В «Ост»",
            defaults={
                "address": "просп. Берестейський, 40-В",
                "city": "Київ",
                "is_active": True,
                "complex": complex_obj,
            },
        )
        if not building_c.complex:
            building_c.complex = complex_obj
            building_c.save()

        # Use building A as primary for issues/residents (building B for second group)
        building = building_a
        building2 = building_b

        self.stdout.write(f"  ✓ Buildings: {building_a.name}, {building_b.name}, {building_c.name}")

        # ── 2. Entrances (під'їзди) ───────────────────────────────────────
        entrance1, _ = Entrance.objects.get_or_create(building=building_a, name="Під'їзд 1")
        entrance2, _ = Entrance.objects.get_or_create(building=building_a, name="Під'їзд 2")
        entrance3, _ = Entrance.objects.get_or_create(building=building_b, name="Під'їзд 1")
        entrance4, _ = Entrance.objects.get_or_create(building=building_b, name="Під'їзд 2")
        entrance5, _ = Entrance.objects.get_or_create(building=building_c, name="Під'їзд 1")
        entrance6, _ = Entrance.objects.get_or_create(building=building_c, name="Під'їзд 2")

        self.stdout.write(
            f"  ✓ Entrances: {Entrance.objects.filter(building__in=[building_a, building_b, building_c]).count()} "
            f"(А: 2, Б: 2, В: 2)"
        )

        # ── 3. Units ─────────────────────────────────────────────────────
        # Building A: entrance1 → units 1-10, entrance2 → units 101-110
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

        # Building B: entrance3 → units 201-210, entrance4 → units 301-310
        for floor in range(1, 6):
            for pos in range(1, 3):
                unit_num = str(200 + (floor - 1) * 2 + pos)
                Unit.objects.get_or_create(
                    entrance=entrance3,
                    number=unit_num,
                    defaults={"floor": floor},
                )
        for floor in range(1, 6):
            for pos in range(1, 3):
                unit_num = str(300 + (floor - 1) * 2 + pos)
                Unit.objects.get_or_create(
                    entrance=entrance4,
                    number=unit_num,
                    defaults={"floor": floor},
                )

        # Building C: entrance5 → units 401-410, entrance6 → units 501-510
        for floor in range(1, 6):
            for pos in range(1, 3):
                unit_num = str(400 + (floor - 1) * 2 + pos)
                Unit.objects.get_or_create(
                    entrance=entrance5,
                    number=unit_num,
                    defaults={"floor": floor},
                )
        for floor in range(1, 6):
            for pos in range(1, 3):
                unit_num = str(500 + (floor - 1) * 2 + pos)
                Unit.objects.get_or_create(
                    entrance=entrance6,
                    number=unit_num,
                    defaults={"floor": floor},
                )

        # ── 4. Superuser ──────────────────────────────────────────────────
        admin, _ = _ensure_user(
            "admin@demo.com",
            username="admin",
            first_name="Олексій",
            last_name="Власенко",
            is_staff=True,
            is_superuser=True,
        )
        self.stdout.write("  ✓ Superuser: admin@demo.com / Demo1234!")

        # ── 4.1. Link admin to Organization ───────────────────────────────
        OrganizationMembership.objects.get_or_create(
            user=admin,
            organization=demo_org,
            defaults={"role": OrgRole.SUPER_ADMIN, "is_active": True},
        )

        # ── 5. Staff ──────────────────────────────────────────────────────
        dispatcher, _ = _ensure_user(
            "dispatcher@demo.com",
            username="dispatcher",
            first_name="Тетяна",
            last_name="Романенко",
            is_staff=True,
        )
        Profile.objects.filter(user=dispatcher).update(
            occupation=Profile.Occupation.ELECTRICIAN,
            gender=Profile.Gender.FEMALE,
            phone_number="+380501234567",
            country_of_origin="UA",
            city_of_origin="Київ",
            bio=(
                "Керуючий ЖК Скандинавія з 2021 року. "
                "Відповідаю за координацію технічних служб, роботу з мешканцями та ОСББ. "
                "На зв'язку 24/7 у критичних ситуаціях."
            ),
        )
        self.stdout.write(f"  ✓ Dispatcher: {dispatcher.email} / Demo1234!")

        # ── 5.1. Link dispatcher to Organization ──────────────────────────
        OrganizationMembership.objects.get_or_create(
            user=dispatcher,
            organization=demo_org,
            defaults={"role": OrgRole.ADMIN, "is_active": True},
        )

        # ── 5.2. Guard ────────────────────────────────────────────────────
        guard, _ = _ensure_user(
            "guard@demo.com",
            username="guard",
            first_name="Василь",
            last_name="Гриценко",
        )
        Profile.objects.filter(user=guard).update(
            occupation=Profile.Occupation.GUARD,
            gender=Profile.Gender.MALE,
            phone_number="+380509876543",
            country_of_origin="UA",
            city_of_origin="Бориспіль",
            bio=(
                "Старший охоронець ЖК Скандинавія. "
                "Несу вахту на КПП з 07:00 до 19:00. "
                "Контролюю в'їзд транспорту та відвідувачів."
            ),
        )
        self.stdout.write(f"  ✓ Guard: {guard.email} / Demo1234!")

        # Link guard to organization
        OrganizationMembership.objects.get_or_create(
            user=guard,
            organization=demo_org,
            defaults={"role": OrgRole.STAFF, "is_active": True},
        )

        # ── 5.3. Plumber ──────────────────────────────────────────────────
        plumber, _ = _ensure_user(
            "plumber@demo.com",
            username="plumber",
            first_name="Микола",
            last_name="Процьків",
        )
        Profile.objects.filter(user=plumber).update(
            occupation=Profile.Occupation.PLUMBER,
            gender=Profile.Gender.MALE,
            phone_number="+380671112233",
            country_of_origin="UA",
            city_of_origin="Біла Церква",
            bio=(
                "Сантехнік ЖК Скандинавія. Стаж 18 років. "
                "Спеціалізація: системи водопостачання, каналізація, теплові вузли. "
                "Виклики приймаю через портал або диспетчера."
            ),
        )
        self.stdout.write(f"  ✓ Plumber: {plumber.email} / Demo1234!")

        # Link plumber to organization
        OrganizationMembership.objects.get_or_create(
            user=plumber,
            organization=demo_org,
            defaults={"role": OrgRole.STAFF, "is_active": True},
        )

        # ── 5.4. Electrician ───────────────────────────────────────────────
        electrician, _ = _ensure_user(
            "electrician@demo.com",
            username="electrician",
            first_name="Андрій",
            last_name="Кравченко",
        )
        Profile.objects.filter(user=electrician).update(
            occupation=Profile.Occupation.ELECTRICIAN,
            gender=Profile.Gender.MALE,
            phone_number="+380674445566",
            country_of_origin="UA",
            city_of_origin="Вишгород",
            bio=(
                "Електрик ЖК. Обслуговую електромережі будинків А, Б, В. "
                "Сертифікований спеціаліст IV групи електробезпеки. "
                "Аварійні виклики — цілодобово."
            ),
        )
        self.stdout.write(f"  ✓ Electrician: {electrician.email} / Demo1234!")

        # Link electrician to organization
        OrganizationMembership.objects.get_or_create(
            user=electrician,
            organization=demo_org,
            defaults={"role": OrgRole.STAFF, "is_active": True},
        )

        # ── 6. Tenant (linked to unit) ────────────────────────────────────
        tenant_unit = units[16]
        tenant_user, _ = _ensure_user(
            "tenant@demo.com",
            username="tenant",
            first_name="Дмитро",
            last_name="Саварин",
        )
        Profile.objects.filter(user=tenant_user).update(
            occupation=Profile.Occupation.TENANT,
            gender=Profile.Gender.MALE,
            phone_number="+380637778899",
            country_of_origin="UA",
            city_of_origin="Київ",
            bio=(
                "Живу в ЖК Скандинавія з 2022 року. "
                "Задоволений інфраструктурою та тихим двором. "
                "Активний учасник ОСББ."
            ),
            unit=tenant_unit,
        )
        tenant_apt, _ = Apartment.objects.get_or_create(
            unit_number=tenant_unit.number,
            defaults={
                "building": building_a.name,
                "floor": tenant_unit.floor or 1,
                "tenant": tenant_user,
            },
        )
        tenant_apt.tenant = tenant_user
        tenant_apt.save()
        _link_unit_apartment(tenant_unit, tenant_apt)

        # Link tenant to organization
        OrganizationMembership.objects.get_or_create(
            user=tenant_user,
            organization=demo_org,
            defaults={"role": OrgRole.RESIDENT, "is_active": True},
        )

        self.stdout.write(f"  ✓ Tenant: {tenant_user.email} / Demo1234! (Кв. {tenant_unit.number})")

        # ── 7. Residents ──────────────────────────────────────────────────
        residents_data = [
            ("resident1@demo.com",  "Іван",     "Петренко",    "resident1",  units[0],  Profile.Gender.MALE,   "+380501110001", "Київ",    "ІТ-спеціаліст, живу в ЖК з відкриття. Ціную швидкий інтернет та тихих сусідів."),
            ("resident2@demo.com",  "Марія",    "Шевченко",    "resident2",  units[2],  Profile.Gender.FEMALE, "+380501110002", "Полтава", "Лікар-педіатр. Мама двох дітей. Завжди рада сусідам і активно беру участь у житті ЖК."),
            ("resident3@demo.com",  "Андрій",   "Бондаренко",  "resident3",  units[4],  Profile.Gender.MALE,   "+380501110003", "Харків",  "Підприємець. Ціную зручну паркову зону та охорону комплексу."),
            ("resident4@demo.com",  "Олена",    "Мельник",     "resident4",  units[6],  Profile.Gender.FEMALE, "+380501110004", "Дніпро",  "Архітектор. Переїхала до Києва 2 роки тому. Захоплююся дизайном інтер'єрів."),
            ("resident5@demo.com",  "Дмитро",   "Коваленко",   "resident5",  units[8],  Profile.Gender.MALE,   "+380501110005", "Київ",    "Фінансовий аналітик. Учасник ОСББ, слідкую за прозорістю витрат на утримання ЖК."),
            ("resident6@demo.com",  "Наталія",  "Литвиненко",  "resident6",  units[10], Profile.Gender.FEMALE, "+380501110006", "Львів",   "Вчителька початкових класів. Організовую суботники та сусідські свята."),
            ("resident7@demo.com",  "Олексій",  "Мороз",       "resident7",  units[12], Profile.Gender.MALE,   "+380501110007", "Запоріжжя", "Інженер-конструктор. Цікавлюся технічним обслуговуванням будинку."),
            ("resident8@demo.com",  "Тетяна",   "Савченко",    "resident8",  units[14], Profile.Gender.FEMALE, "+380501110008", "Вінниця", "Дизайнерка інтер'єрів. Живу з чоловіком та кошеням Гі. Обожнюю балкон з видом на парк."),
        ]
        residents = []
        for email, first, last, username, unit, gender, phone, city, bio in residents_data:
            user, _ = _ensure_user(email, username=username, first_name=first, last_name=last)
            Profile.objects.filter(user=user).update(
                occupation=Profile.Occupation.TENANT,
                gender=gender,
                phone_number=phone,
                country_of_origin="UA",
                city_of_origin=city,
                bio=bio,
                unit=unit,
            )
            apt, _ = Apartment.objects.get_or_create(
                unit_number=unit.number,
                defaults={
                    "building": building_a.name,
                    "floor": unit.floor or 1,
                    "tenant": user,
                },
            )
            apt.tenant = user
            apt.save()
            _link_unit_apartment(unit, apt)

            # Link resident to organization
            OrganizationMembership.objects.get_or_create(
                user=user,
                organization=demo_org,
                defaults={"role": OrgRole.RESIDENT, "is_active": True},
            )

            residents.append((user, unit, apt))
            self.stdout.write(f"  ✓ Resident: {email} (кв. {unit.number})")

        # ── 8. Categories ─────────────────────────────────────────────────
        categories = []
        for name, sla in [
            ("Сантехніка", 24),
            ("Електрика", 48),
            ("Загальні приміщення", 72),
            ("Ліфт", 8),
            ("Опалення та ГВП", 24),
            ("Вентиляція", 48),
            ("Фасад та покрівля", 120),
            ("Двір та паркінг", 72),
        ]:
            cat, _ = Category.objects.get_or_create(name=name, defaults={"sla_hours": sla})
            categories.append(cat)

        # ── 9. Issues (16 realistic requests) ────────────────────────────
        issue_data = [
            ("Протікає труба у ванній",              "Сантехніка",          "Труба під раковиною в санвузлі протікає вже три дні. Вода збирається на підлозі і просочується до сусідів знизу. Прошу якнайшвидшого виїзду майстра."),
            ("Не працює розетка в кухні",            "Електрика",           "Розетка біля холодильника перестала працювати після грози. Мікрохвильова й холодильник не отримують живлення. Інші розетки — в нормі."),
            ("Ліфт застрягає між поверхами",         "Ліфт",                "Ліфт корпусу А зупиняється між 5 і 6 поверхами. Двічі застрявав з мешканцями. Потребує термінової перевірки ліфтової компанії."),
            ("Бруд і покинуте сміття у під'їзді",    "Загальні приміщення", "На сходовому майданчику 2 поверху під'їзд №1 тиждень не прибирали. Пакети зі сміттям стоять з минулої середи. Неприємний запах."),
            ("Немає гарячої води третій день",       "Сантехніка",          "Гаряча вода відсутня з понеділка ранку. Холодна подається без проблем. Ні попереднього повідомлення, ні пояснення від управителя."),
            ("Перегоріло освітлення на 4 поверсі",   "Електрика",           "На 4-му поверсі під'їзду №2 не горять 3 лампи в коридорі. Ввечері там зовсім темно — небезпечно для мешканців і дітей."),
            ("Ліфт видає металевий скрип",           "Ліфт",                "При русі вгору чути сильний металевий скрегіт. Виникає між 3-м та 7-м поверхами. Мешканці бояться користуватися ліфтом."),
            ("Зламані поштові скриньки",              "Загальні приміщення", "Шість поштових скриньок у вестибюлі корпусу Б не замикаються — дверцята відламані або погнуті. Пошта й реклама висипаються на підлогу."),
            ("Засмічена каналізація у ванній",       "Сантехніка",          "Вода в ванні не стікає більше 30 хвилин після купання. Тросик не допомагає. Можливо засміченість в стояку — сусіди знизу теж скаржаться."),
            ("Запах сирості з підвалу",              "Загальні приміщення", "З підвального приміщення корпусу А постійно надходить запах цвілі та сирості. Помітно на першому поверсі. Можливо, прорив каналізації або підтоплення."),
            ("Холодна батарея у спальні",            "Опалення та ГВП",     "Радіатор у спальні холодний, хоча в решті кімнат опалення працює нормально. Вже тиждень температура в кімнаті не піднімається вище 15°С."),
            ("Гучна вібрація вентшахти",             "Вентиляція",          "Вентиляційна шахта в кухні вібрує та видає низький гул, особливо вночі. Заважає спати. Почалося після ремонту на технічному поверсі."),
            ("Тріщина на фасаді корпусу Б",          "Фасад та покрівля",   "На рівні 4-5 поверхів із зовнішнього боку корпусу Б з'явилася горизонтальна тріщина шириною ~1 см. Зростає від осені. Потрібна оцінка."),
            ("Протікання даху після дощу",           "Фасад та покрівля",   "Після кожного дощу на стелі у ванній кімнаті 5-го поверху з'являються темні плями та краплі. Шпаклівка вже відшаровується."),
            ("Не спрацьовує домофон на вході",       "Електрика",           "Домофон корпусу А не реагує на натискання кнопок з 08:00 до 18:00 — можливо, перегрів блоку живлення. Ввечері іноді працює."),
            ("Вибоїни на в'їзді до паркінгу",        "Двір та паркінг",     "На в'їзді до підземного паркінгу утворилися три глибокі вибоїни після зимових морозів. Вже дряпали низькі автомобілі. Потрібен ямковий ремонт."),
        ]

        from apps.notifications.signals import cache_issue_old_state, on_issue_saved
        from django.db.models.signals import post_save, pre_save

        pre_save.disconnect(cache_issue_old_state, sender=Issue)
        post_save.disconnect(on_issue_saved, sender=Issue)
        statuses = ["reported", "accepted", "in_progress", "done", "rejected"]
        try:
            cat_map = {c.name: c for c in categories}
            for i, (title, cat_name, description) in enumerate(issue_data):
                user, unit, apt = residents[i % len(residents)]
                cat = cat_map[cat_name]
                status = statuses[i % len(statuses)]
                due = now + timedelta(hours=cat.sla_hours) - timedelta(hours=random.randint(0, 72))
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
                if created and status == "done":
                    issue.resolved_on = now.date()
                    issue.save()
        finally:
            pre_save.connect(cache_issue_old_state, sender=Issue)
            post_save.connect(on_issue_saved, sender=Issue)

        self.stdout.write(f"  ✓ Created/verified {len(issue_data)} service requests")

        # ── 10. Announcements (10) ────────────────────────────────────────
        announcements_data = [
            (
                "⚠️ Планове відключення води 18 квітня",
                "18 квітня з 09:00 до 17:00 буде відключена холодна вода у корпусах А та Б у зв'язку з плановою заміною засувки на введенні. Просимо завчасно запастися водою. Гаряча вода — без змін.",
            ),
            (
                "🌿 Суботник у дворі — 20 квітня о 10:00",
                "Запрошуємо всіх мешканців на весняний суботник! Прибираємо двір, висаджуємо квіти на клумбах, встановлюємо нові лавки. Інвентар надається. Дітям — солодкий приз від ОСББ 🎉",
            ),
            (
                "🔧 Технічний огляд ліфтів — 22 квітня",
                "22 квітня з 10:00 до 14:00 фахівці ліфтової компанії проведуть планову перевірку та мастило ліфтів у всіх трьох корпусах. Можливі короткочасні зупинки по 10-15 хвилин.",
            ),
            (
                "🚗 Нові правила паркування з 1 травня",
                "З 1 травня вводяться номерні місця у наземному паркінгу. Машини без реєстрації будуть евакуйовані. Для реєстрації автомобіля звертайтесь до управителя або заповніть форму на порталі.",
            ),
            (
                "📋 Збори ОСББ — 26 квітня о 18:30",
                "Щорічні загальні збори мешканців ЖК Скандинавія. Порядок денний: звіт управителя за 2025 рік, затвердження кошторису на 2026 рік, питання ремонту даху та встановлення зарядних станцій. Явка обов'язкова!",
            ),
            (
                "🎪 Відкриття літнього кіно у дворі — 1 травня",
                "1 травня о 21:00 відбудеться перший сеанс літнього кінотеатру ЖК Скандинавія просто неба! Показуємо «Мій сусід Тоторо». Принесіть пледи та гарний настрій 🍿",
            ),
            (
                "📦 Нова поштомат-станція у вестибюлі корпусу А",
                "Повідомляємо, що у вестибюлі корпусу А встановлено поштомат Nova Poshta. Тепер можна отримувати та відправляти посилки 24/7 без черг у відділенні. Зручно для всіх мешканців ЖК.",
            ),
            (
                "🔒 Оновлення системи відеоспостереження",
                "До 30 квітня буде замінено 12 камер відеоспостереження на входах, паркінгу та в ліфтах на нові IP-камери з роздільною здатністю 4K. Запис зберігатиметься 30 діб. Безпека — наш пріоритет.",
            ),
            (
                "💧 Заміна лічильників води — квітень",
                "З 15 по 30 квітня відбудеться планова заміна лічильників холодної та гарячої води у квартирах. Майстер телефонуватиме за добу до приходу. Графік за квартирами — на дошці оголошень та в порталі.",
            ),
            (
                "🏗️ Капітальний ремонт даху корпусу В",
                "З 5 травня розпочинається капітальний ремонт дахового покриття корпусу В «Ост». Роботи триватимуть 3-4 тижні. Просимо мешканців верхніх поверхів накрити речі на лоджіях. Вибачаємося за тимчасові незручності.",
            ),
        ]

        from apps.notifications.signals import on_announcement_created

        post_save.disconnect(on_announcement_created, sender=Announcement)
        try:
            for title, body in announcements_data:
                Announcement.objects.get_or_create(
                    building=building_a,
                    title=title,
                    defaults={"body": body, "is_active": True},
                )
        finally:
            post_save.connect(on_announcement_created, sender=Announcement)

        self.stdout.write(f"  ✓ Created/verified {len(announcements_data)} announcements")

        # ── 11. News articles ─────────────────────────────────────────────
        from apps.news.models import News, NewsCategory

        cat_info, _      = NewsCategory.objects.get_or_create(name="Новини ЖК",       defaults={"color": "#1E40AF"})
        cat_events, _    = NewsCategory.objects.get_or_create(name="Події",            defaults={"color": "#065F46"})
        cat_maintenance, _ = NewsCategory.objects.get_or_create(name="Обслуговування", defaults={"color": "#92400E"})
        cat_safety, _    = NewsCategory.objects.get_or_create(name="Безпека",          defaults={"color": "#991B1B"})
        cat_community, _ = NewsCategory.objects.get_or_create(name="Спільнота",        defaults={"color": "#5B21B6"})

        news_data = [
            {
                "title": "🏠 ApartmentOS Portal — ваш особистий кабінет мешканця",
                "excerpt": "Всі послуги ЖК Скандинавія тепер у вашому смартфоні: заявки, пропуски, новини.",
                "body": (
                    "Шановні мешканці ЖК Скандинавія!\n\n"
                    "Раді представити оновлений портал управління ApartmentOS — ваш єдиний цифровий центр для взаємодії з ЖК.\n\n"
                    "Що доступно прямо зараз:\n"
                    "• Подача заявок на технічне обслуговування — онлайн, без черг\n"
                    "• Замовлення перепустки для гостей або транспорту\n"
                    "• Оголошення та новини ЖК в режимі реального часу\n"
                    "• Особистий профіль з історією звернень\n\n"
                    "Для входу використовуйте email, що ви надавали при реєстрації. "
                    "Технічна підтримка: support@skandi.ua або через чат у порталі."
                ),
                "category": cat_info,
                "pinned": True,
            },
            {
                "title": "🏆 ЖК Скандинавія увійшов у топ-10 найбезпечніших ЖК Києва",
                "excerpt": "Незалежний рейтинг LiveKyiv 2026 визнав наш комплекс одним із найкращих за рівнем безпеки.",
                "body": (
                    "За результатами щорічного рейтингу LiveKyiv Housing Security Index 2026, "
                    "ЖК Скандинавія посів 7-е місце серед 120 житлових комплексів Києва.\n\n"
                    "Критерії оцінки: система відеоспостереження, охорона 24/7, контрольований в'їзд, "
                    "рівень злочинності поблизу, пожежна безпека.\n\n"
                    "Це стало можливим завдяки нашій спільноті та активності мешканців у вирішенні питань безпеки. "
                    "Дякуємо всім, хто повідомляє про підозрілі ситуації через портал!"
                ),
                "category": cat_safety,
                "pinned": True,
            },
            {
                "title": "📅 Графік технічного обслуговування на квітень 2026",
                "excerpt": "Повний графік планових робіт з обслуговування інженерних систем ЖК у квітні.",
                "body": (
                    "Квітень 2026 — планові технічні роботи:\n\n"
                    "1-15 квітня: Заміна лічильників холодної та гарячої води (за квартирним графіком)\n"
                    "8 квітня: Промивка системи опалення корпусу А\n"
                    "12 квітня: Обслуговування насосної станції\n"
                    "15 квітня: Дезінфекція підвальних приміщень\n"
                    "18 квітня: Відключення води (09:00–17:00), корпуси А та Б\n"
                    "22 квітня: Огляд та мастило ліфтів\n"
                    "25 квітня: Перевірка аварійного освітлення\n\n"
                    "Про всі відключення повідомлятимемо додатково у порталі та на дошках оголошень."
                ),
                "category": cat_maintenance,
                "pinned": False,
            },
            {
                "title": "🌳 Результати весняного озеленення двору",
                "excerpt": "Висаджено 24 дерева, 150 кущів та понад 500 квіток. Дякуємо всім учасникам!",
                "body": (
                    "Цієї весни мешканці ЖК Скандинавія побили власний рекорд активності!\n\n"
                    "У трьох суботниках взяли участь понад 60 людей. Разом ми:\n"
                    "• Висадили 24 молодих дерева (клени, горобини, черешні)\n"
                    "• Облаштували 4 нові квіткові клумби\n"
                    "• Встановили 6 нових лавок та 3 урни\n"
                    "• Пофарбували паркан та бордюри\n\n"
                    "Окрема подяка Наталії Литвиненко (кв. 101) за організацію та закупівлю саджанців. "
                    "Двір ЖК Скандинавія — зеленіший з кожним роком!"
                ),
                "category": cat_community,
                "pinned": False,
            },
            {
                "title": "⚡ Встановлення зарядних станцій для електромобілів",
                "excerpt": "ОСББ проголосував за встановлення 4 зарядних станцій EV на паркінгу ЖК.",
                "body": (
                    "На зборах ОСББ у березні мешканці проголосували за встановлення 4 зарядних станцій "
                    "для електромобілів на підземному паркінгу.\n\n"
                    "Деталі проєкту:\n"
                    "• Тип: AC зарядка 22 кВт (Type 2)\n"
                    "• Кількість: 4 станції по 2 розʼєми кожна\n"
                    "• Розташування: місця P12–P15 підземного паркінгу\n"
                    "• Очікуваний запуск: 1 червня 2026\n"
                    "• Оплата: через мобільний додаток або банківську картку\n\n"
                    "Попередній запис на постійне паркомісце біля зарядки — через портал."
                ),
                "category": cat_info,
                "pinned": False,
            },
            {
                "title": "🎉 День народження ЖК Скандинавія — 4 роки разом!",
                "excerpt": "15 травня відзначаємо 4-річчя нашого ЖК. Святкова програма для мешканців та дітей.",
                "body": (
                    "15 травня 2026 року ЖК Скандинавія святкує своє чотириріччя!\n\n"
                    "Програма:\n"
                    "12:00 — Відкриття свята у дворі корпусу А\n"
                    "12:30 — Майстер-клас з живопису для дітей\n"
                    "13:00 — Барбекю та пікнік (підготовка ОСББ)\n"
                    "15:00 — Спортивні змагання: волейбол, бадмінтон\n"
                    "18:00 — Конкурс на найкращий балкон ЖК 2026\n"
                    "20:00 — Кіно просто неба\n\n"
                    "Вхід вільний для всіх мешканців. Дітям — подарунки від ОСББ!"
                ),
                "category": cat_events,
                "pinned": False,
            },
            {
                "title": "🔥 Нагадування про правила пожежної безпеки",
                "excerpt": "Будь ласка, ознайомтесь з правилами та переконайтесь, що евакуаційні виходи не заблоковані.",
                "body": (
                    "Нагадуємо мешканцям основні правила пожежної безпеки в ЖК Скандинавія:\n\n"
                    "🚫 Заборонено:\n"
                    "• Залишати речі на сходових клітках та евакуаційних шляхах\n"
                    "• Зберігати легкозаймисті речовини у підвалах\n"
                    "• Курити в під'їздах, ліфтах та підвалах\n\n"
                    "✅ Обов'язково:\n"
                    "• Знати розташування вогнегасників на вашому поверсі\n"
                    "• Перевірити справність датчика диму у квартирі\n"
                    "• Запам'ятати номер пожежної охорони: 101\n\n"
                    "Наступна планова перевірка систем: 25 квітня о 10:00."
                ),
                "category": cat_safety,
                "pinned": False,
            },
            {
                "title": "📊 Фінансовий звіт ОСББ за І квартал 2026",
                "excerpt": "Детальний звіт про надходження та витрати на утримання ЖК у січні-березні 2026.",
                "body": (
                    "Шановні мешканці, публікуємо фінансовий звіт за І квартал 2026 року.\n\n"
                    "Надходження (грн):\n"
                    "• Внески на утримання: 487 200\n"
                    "• Орендна плата (приміщення): 18 000\n"
                    "• Штрафи та пені: 2 340\n"
                    "Разом: 507 540\n\n"
                    "Витрати (грн):\n"
                    "• Зарплата персоналу: 198 000\n"
                    "• Комунальні послуги (загальні): 87 600\n"
                    "• Технічне обслуговування: 124 500\n"
                    "• Прибирання та озеленення: 43 200\n"
                    "• Адмін витрати: 12 000\n"
                    "Разом: 465 300\n\n"
                    "Залишок на рахунку ОСББ: 42 240 грн (резервний фонд).\n"
                    "Повний звіт — у розділі документів порталу."
                ),
                "category": cat_info,
                "pinned": False,
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

        # ── 12. Vehicle passes (15 realistic) ────────────────────────────
        pass_data = [
            ("АА1234ВВ", "Доставка меблів IKEA (потрібна вантажна рампа)", 1),
            ("ВН5678КА", "Гості з Полтави — брат з сім'єю", 0),
            ("АІ9012НР", "Таксі Bolt до аеропорту Бориспіль", -1),
            ("СА3456ОЕ", "Вантажівка для переїзду кв. 7", 2),
            ("АА7890ТТ", "День народження — гості увечері", 3),
            ("ВС1111КК", "Кур'єр Нова Пошта (посилка негабаритна)", 0),
            ("АА2222НН", "Майстер з ремонту кондиціонера", -2),
            ("КА3333ОО", "Батьки з Харкова на тижень", 4),
            ("ВН4444РР", "Евакуатор — не заводиться авто", -1),
            ("АА5555СС", "Доставка продуктів Zakaz.ua", 0),
            ("ТТ6666ВВ", "Бригада електриків (замовлення управителя)", 1),
            ("АА7777ММ", "Рієлтор на огляд квартири 105", 2),
            ("ВА8888НН", "Піца та суші — вечірка у кв. 3", 0),
            ("АА9999КК", "Сантехнік — аварійний виклик", -3),
            ("ОА0000РР", "Лікар-педіатр виклик додому", 1),
        ]

        from apps.notifications.signals import on_pass_saved
        from apps.passes.models import VehiclePass as VehiclePassModel

        post_save.disconnect(on_pass_saved, sender=VehiclePassModel)
        try:
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
                    vp.closed_at = now - timedelta(hours=random.randint(1, 72))
                    vp.save()
        finally:
            post_save.connect(on_pass_saved, sender=VehiclePassModel)

        self.stdout.write(f"  ✓ Created/verified {len(pass_data)} vehicle passes")

        # ── 13. Organization-scoped SiteSettings and Contacts ──────────────
        org_site, _ = SiteSettings.objects.get_or_create(organization=demo_org)
        org_site.platform_name = "EstateOS"
        org_site.complex_name = "ЖК Скандинавія"
        org_site.complex_address = "просп. Берестейський, 40-В, Київ"
        org_site.support_email = "support@skandinaviya.ua"
        org_site.support_phone = "+38 (044) 000-00-00"
        org_site.primary_color = "#3D7A8A"
        org_site.hero_title = "Ласкаво просимо до ЖК Скандинавія"
        org_site.hero_subtitle = "Ви новий мешканець? Або вже зареєстровані?"
        org_site.cta_text = "Увійти"
        org_site.footer_text = "ЖК Скандинавія | EstateOS © 2026"
        org_site.save()
        self.stdout.write(f"  ✓ Organization SiteSettings linked")

        # Organization-linked contacts
        ContactPerson.objects.get_or_create(
            organization=demo_org,
            role=ContactPerson.Role.MANAGER,
            defaults={
                "name": "Тетяна Романенко",
                "position": "Керуюча ЖК",
                "phone": "+38 (044) 000-11-22",
                "email": "manager@skandinaviya.ua",
                "working_hours": "Пн-Пт 09:00-18:00",
                "is_active": True,
                "order": 0,
            },
        )
        ContactPerson.objects.get_or_create(
            organization=demo_org,
            role=ContactPerson.Role.GUARD,
            defaults={
                "name": "Василь Гриценко",
                "position": "Старший охоронець",
                "phone": "+38 (044) 000-33-44",
                "working_hours": "24/7",
                "is_active": True,
                "order": 1,
            },
        )
        ContactPerson.objects.get_or_create(
            organization=demo_org,
            role=ContactPerson.Role.TECHNICIAN,
            defaults={
                "name": "Микола Процьків",
                "position": "Сантехнік",
                "phone": "+38 (067) 111-22-33",
                "email": "plumber@skandinaviya.ua",
                "working_hours": "Пн-Пт 08:00-17:00",
                "is_active": True,
                "order": 2,
            },
        )
        ContactPerson.objects.get_or_create(
            organization=demo_org,
            role=ContactPerson.Role.TECHNICIAN,
            defaults={
                "name": "Андрій Кравченко",
                "position": "Електрик",
                "phone": "+38 (067) 444-55-66",
                "email": "electrician@skandinaviya.ua",
                "working_hours": "Пн-Пт 08:00-17:00, аварійні — цілодобово",
                "is_active": True,
                "order": 3,
            },
        )
        ContactPerson.objects.get_or_create(
            organization=demo_org,
            role=ContactPerson.Role.ACCOUNTANT,
            defaults={
                "name": "Ірина Ковальчук",
                "position": "Головний бухгалтер ОСББ",
                "phone": "+38 (044) 000-55-66",
                "email": "accounting@skandinaviya.ua",
                "working_hours": "Пн-Пт 09:00-17:00",
                "is_active": True,
                "order": 4,
            },
        )
        ContactPerson.objects.get_or_create(
            organization=demo_org,
            role=ContactPerson.Role.EMERGENCY,
            defaults={
                "name": "Аварійна служба ЖК",
                "position": "Диспетчерська",
                "phone": "+38 (044) 000-77-88",
                "working_hours": "24/7",
                "is_emergency": True,
                "is_active": True,
                "order": 5,
            },
        )
        self.stdout.write(f"  ✓ Organization contacts created (6 contact persons)")

        # ── 13. Posts & Tags ─────────────────────────────────────────────
        posts_data = [
            {
                "title": "Як правильно подавати заявку на ремонт",
                "body": (
                    "Покрокова інструкція для мешканців ЖК:\n\n"
                    "1. Зайдіть у свій кабінет на порталі ApartmentOS\n"
                    "2. Натисніть «Створити заявку»\n"
                    "3. Оберіть категорію (сантехніка, електрика, ліфт тощо)\n"
                    "4. Опишіть проблему та додайте фото\n"
                    "5. Чекайте на підтвердження від диспетчера\n\n"
                    "Якщо заявка терміновая — зателефонуйте на гарячу лінію."
                ),
                "tags": ["ремонт", "заявки", "інструкція"],
                "author": dispatcher,
                "upvotes": 12,
            },
            {
                "title": "Правила паркування на території ЖК",
                "body": (
                    "Шановні мешканці!\n\n"
                    "Нагадуємо правила паркування:\n"
                    "- Паркуватися лише на відведених місцях\n"
                    "- Гостьові перепустки оформляються через портал\n"
                    "- Заборонено блокувати проїзди та пожежні виходи\n"
                    "- Порушники отримають попередження\n\n"
                    "Дякуємо за розуміння!"
                ),
                "tags": ["паркування", "правила", "перепустки"],
                "author": dispatcher,
                "upvotes": 8,
            },
            {
                "title": "Графік роботи сантехніка",
                "body": (
                    "Сантехнік ЖК Скандинавія працює:\n\n"
                    "Пн-Пт: 09:00 — 18:00\n"
                    "Сб: 10:00 — 14:00\n"
                    "Нд: вихідний\n\n"
                    "Для термінових випадків (прорив труби, затоплення) — "
                    "зверніться до аварійної служби за номером +38 (044) 000-77-88 (цілодобово)."
                ),
                "tags": ["сантехніка", "графік", "контакти"],
                "author": plumber,
                "upvotes": 15,
            },
            {
                "title": "Економія електроенергії: поради для мешканців",
                "body": (
                    "Кілька простих порад, як зменшити рахунки за електрику:\n\n"
                    "1. Використовуйте LED-лампи замість ламп розжарювання\n"
                    "2. Вимикайте світло, виходячи з кімнати\n"
                    "3. Не залишайте техніку в режимі очікування\n"
                    "4. Встановіть двозонний лічильник\n"
                    "5. Використовуйте пральну машину на повному завантаженні\n\n"
                    "Разом ми зробимо наш ЖК більш енергоефективним!"
                ),
                "tags": ["електрика", "економія", "поради"],
                "author": electrician,
                "upvotes": 20,
            },
            {
                "title": "Підготовка до опалювального сезону",
                "body": (
                    "Опалювальний сезон починається 15 жовтня.\n\n"
                    "Для підготовки просимо:\n"
                    "- Перевірте стан радіаторів у своїй квартирі\n"
                    "- Якщо є проблеми з батареями — подайте заявку до 1 жовтня\n"
                    "- Не закривайте радіатори меблями для кращої циркуляції тепла\n"
                    "- При виявленні витоку — негайно повідомте диспетчера\n\n"
                    "Бажаємо теплої зими!"
                ),
                "tags": ["опалення", "сезон", "підготовка"],
                "author": dispatcher,
                "upvotes": 10,
            },
            {
                "title": "Нові правила сортування сміття",
                "body": (
                    "З 1 числа вводяться нові правила сортування:\n\n"
                    "🟡 Жовтий контейнер — пластик та метал\n"
                    "🔵 Синій контейнер — папір та картон\n"
                    "🟢 Зелений контейнер — скло\n"
                    "⚫ Чорний контейнер — змішані відходи\n\n"
                    "Контейнери розташовані біля кожного під'їзду. "
                    "Просимо дотримуватись правил!"
                ),
                "tags": ["екологія", "правила", "сортування"],
                "author": dispatcher,
                "upvotes": 6,
            },
        ]

        for post_data in posts_data:
            tags = post_data.pop("tags")
            upvotes_count = post_data.pop("upvotes")
            post_data["organization"] = demo_org
            post, created = Post.objects.get_or_create(
                title=post_data["title"],
                defaults=post_data,
            )
            if created:
                post.upvotes = upvotes_count
                post.save(update_fields=["upvotes"])
                post.tags.set(tags)

        self.stdout.write(f"  ✓ Posts created: {Post.objects.count()} with tags")

        # ── 14. Summary ───────────────────────────────────────────────────
        self.stdout.write(self.style.SUCCESS(
            "\n✅ ЖК Скандинавія seed complete!\n"
            f"   Комплекс: {complex_obj.name}\n"
            f"   Будинки: {building_a.name}, {building_b.name}, {building_c.name}\n"
            f"   Під'їзди: {Entrance.objects.count()}, Квартири: {Unit.objects.count()}\n"
            f"   Користувачі: {User.objects.count()}\n"
            f"   Заявки: {Issue.objects.count()}\n"
            f"   Оголошення: {Announcement.objects.count()}\n"
            f"   Новини: {News.objects.filter(is_published=True).count()}\n"
            f"   Публікації: {Post.objects.count()}\n"
            f"   Пропуски: {VehiclePass.objects.count()}\n"
            "\n   Логіни (пароль: Demo1234!):\n"
            "   ──────────────────────────────────────────\n"
            "   dispatcher@demo.com  — керуючий (staff)\n"
            "   guard@demo.com       — охоронець\n"
            "   plumber@demo.com     — сантехнік\n"
            "   electrician@demo.com — електрик\n"
            f"   tenant@demo.com      — мешканець кв. {tenant_unit.number}\n"
            "   resident1..8@demo.com — мешканці\n"
            "   admin@demo.com       — superuser (Django admin)\n"
        ))
