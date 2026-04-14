"""
Migration: Apartment.unit_number — прибираємо глобальний unique=True,
додаємо unique_together = [("building", "unit_number")].

Причина: квартира №1 може існувати в різних будинках — це нормально.
Глобальний unique=True блокував мешканців при виборі квартири в профілі
якщо той самий номер вже був у іншому будинку (помилка «вже зайнятий»).
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("apartments", "0002_add_organization_fks"),
    ]

    operations = [
        # 1. Прибираємо глобальний unique constraint з колонки
        migrations.AlterField(
            model_name="apartment",
            name="unit_number",
            field=models.CharField(max_length=10, verbose_name="Unit Number"),
        ),
        # 2. Додаємо composite unique: (building, unit_number)
        migrations.AlterUniqueTogether(
            name="apartment",
            unique_together={("building", "unit_number")},
        ),
    ]
