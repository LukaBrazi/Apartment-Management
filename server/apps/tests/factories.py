"""Factory Boy factories for all apps."""
import factory
from django.contrib.auth import get_user_model
from factory.django import DjangoModelFactory

from apps.apartments.models import Apartment, Building, Entrance, Unit

User = get_user_model()


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User
        skip_postgeneration_save = True

    email = factory.Sequence(lambda n: f"user{n}@test.com")
    username = factory.Sequence(lambda n: f"user{n}")
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    password = factory.PostGenerationMethodCall("set_password", "testpass123")
    is_active = True


class AdminUserFactory(UserFactory):
    is_staff = True
    is_superuser = True


class BuildingFactory(DjangoModelFactory):
    class Meta:
        model = Building

    name = factory.Sequence(lambda n: f"Building {n}")
    address = factory.Faker("street_address")
    city = "Kyiv"
    is_active = True


class EntranceFactory(DjangoModelFactory):
    class Meta:
        model = Entrance

    building = factory.SubFactory(BuildingFactory)
    name = factory.Sequence(lambda n: str(n + 1))


class UnitFactory(DjangoModelFactory):
    class Meta:
        model = Unit

    entrance = factory.SubFactory(EntranceFactory)
    number = factory.Sequence(lambda n: str(n + 1))
    floor = factory.Sequence(lambda n: (n % 9) + 1)


class ApartmentFactory(DjangoModelFactory):
    class Meta:
        model = Apartment

    unit_number = factory.Sequence(lambda n: f"A{n:03d}")
    building = factory.Sequence(lambda n: f"Block {n}")
    floor = factory.Sequence(lambda n: (n % 9) + 1)


class CategoryFactory(DjangoModelFactory):
    class Meta:
        model = "issues.Category"

    name = factory.Sequence(lambda n: f"Category {n}")
    sla_hours = 72


class IssueFactory(DjangoModelFactory):
    class Meta:
        model = "issues.Issue"

    apartment = factory.SubFactory(ApartmentFactory)
    reported_by = factory.SubFactory(UserFactory)
    title = factory.Sequence(lambda n: f"Issue {n}")
    description = factory.Faker("text", max_nb_chars=200)
    status = "reported"
    priority = "low"
