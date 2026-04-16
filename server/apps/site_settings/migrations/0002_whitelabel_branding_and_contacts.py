# Generated migration for white-label SaaS foundation
# Adds platform identity, branding, and contact person management

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("site_settings", "0001_initial"),
    ]

    operations = [
        # Expand SiteSettings with platform identity
        migrations.AddField(
            model_name="sitesettings",
            name="platform_name",
            field=models.CharField(
                default="EstateOS",
                help_text="The name of the property management platform (white-label).",
                max_length=100,
                verbose_name="platform name",
            ),
        ),
        migrations.AddField(
            model_name="sitesettings",
            name="platform_tagline",
            field=models.CharField(
                blank=True,
                default="Сучасне управління нерухомістю",
                help_text="Short platform tagline or slogan.",
                max_length=200,
                verbose_name="platform tagline",
            ),
        ),
        migrations.AddField(
            model_name="sitesettings",
            name="logo_url",
            field=models.CharField(
                blank=True,
                default="",
                help_text="External URL to logo or uploaded file path.",
                max_length=500,
                verbose_name="logo URL",
            ),
        ),
        migrations.AddField(
            model_name="sitesettings",
            name="favicon_url",
            field=models.CharField(
                blank=True,
                default="",
                help_text="External URL to favicon or uploaded file path.",
                max_length=500,
                verbose_name="favicon URL",
            ),
        ),
        migrations.AddField(
            model_name="sitesettings",
            name="primary_color",
            field=models.CharField(
                default="#3D7A8A",
                help_text="Hex color code for primary branding (e.g., #3D7A8A).",
                max_length=7,
                verbose_name="primary color",
            ),
        ),
        migrations.AddField(
            model_name="sitesettings",
            name="secondary_color",
            field=models.CharField(
                default="#1C2B3A",
                help_text="Hex color code for secondary branding (e.g., #1C2B3A).",
                max_length=7,
                verbose_name="secondary color",
            ),
        ),
        migrations.AddField(
            model_name="sitesettings",
            name="complex_name",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Name of the residential complex (ЖК/містечка). Overrides current_complex name.",
                max_length=200,
                verbose_name="complex name",
            ),
        ),
        migrations.AddField(
            model_name="sitesettings",
            name="complex_address",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Full address of the complex.",
                max_length=500,
                verbose_name="complex address",
            ),
        ),
        migrations.AddField(
            model_name="sitesettings",
            name="complex_description",
            field=models.TextField(
                blank=True,
                default="",
                help_text="Detailed description of the residential complex.",
                verbose_name="complex description",
            ),
        ),
        migrations.AddField(
            model_name="sitesettings",
            name="support_email",
            field=models.EmailField(
                blank=True,
                default="",
                max_length=254,
                verbose_name="support email",
            ),
        ),
        migrations.AddField(
            model_name="sitesettings",
            name="support_phone",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Phone number for support inquiries.",
                max_length=30,
                verbose_name="support phone",
            ),
        ),
        migrations.AddField(
            model_name="sitesettings",
            name="support_hours",
            field=models.CharField(
                blank=True,
                default="Пн-Пт 09:00-18:00",
                help_text="Support availability (e.g., 'Пн-Пт 09:00-18:00').",
                max_length=100,
                verbose_name="support hours",
            ),
        ),
        migrations.AddField(
            model_name="sitesettings",
            name="telegram_url",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Link to Telegram channel or bot (e.g., https://t.me/yourbot).",
                max_length=200,
                verbose_name="telegram URL",
            ),
        ),
        migrations.AddField(
            model_name="sitesettings",
            name="viber_url",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Link to Viber community or bot.",
                max_length=200,
                verbose_name="viber URL",
            ),
        ),
        migrations.AddField(
            model_name="sitesettings",
            name="footer_text",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Copyright or footer text.",
                max_length=300,
                verbose_name="footer text",
            ),
        ),
        migrations.AddField(
            model_name="sitesettings",
            name="terms_url",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Link to terms of service page.",
                max_length=200,
                verbose_name="terms of service URL",
            ),
        ),
        migrations.AddField(
            model_name="sitesettings",
            name="privacy_url",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Link to privacy policy page.",
                max_length=200,
                verbose_name="privacy policy URL",
            ),
        ),
        migrations.AddField(
            model_name="sitesettings",
            name="meta_title",
            field=models.CharField(
                blank=True,
                default="",
                help_text="HTML meta title tag for SEO.",
                max_length=60,
                verbose_name="meta title",
            ),
        ),
        migrations.AddField(
            model_name="sitesettings",
            name="meta_description",
            field=models.CharField(
                blank=True,
                default="",
                help_text="HTML meta description tag for SEO.",
                max_length=160,
                verbose_name="meta description",
            ),
        ),
        # Create ContactPerson model
        migrations.CreateModel(
            name="ContactPerson",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "name",
                    models.CharField(max_length=150, verbose_name="name"),
                ),
                (
                    "role",
                    models.CharField(
                        choices=[
                            ("manager", "Управитель"),
                            ("technician", "Технічний спеціаліст"),
                            ("guard", "Охорона"),
                            ("accountant", "Бухгалтерія"),
                            ("emergency", "Аварійна служба"),
                            ("other", "Інше"),
                        ],
                        default="other",
                        max_length=20,
                        verbose_name="role",
                    ),
                ),
                (
                    "position",
                    models.CharField(
                        blank=True,
                        help_text="Job title (e.g., 'Головний інженер').",
                        max_length=100,
                        verbose_name="position",
                    ),
                ),
                (
                    "phone",
                    models.CharField(
                        blank=True, max_length=30, verbose_name="phone"
                    ),
                ),
                (
                    "email",
                    models.EmailField(
                        blank=True, max_length=254, verbose_name="email"
                    ),
                ),
                (
                    "telegram",
                    models.CharField(
                        blank=True,
                        help_text="Telegram handle or username (without @).",
                        max_length=100,
                        verbose_name="telegram",
                    ),
                ),
                (
                    "photo",
                    models.ImageField(
                        blank=True, null=True, upload_to="contacts/", verbose_name="photo"
                    ),
                ),
                (
                    "is_emergency",
                    models.BooleanField(
                        default=False,
                        help_text="Show in emergency services section.",
                        verbose_name="emergency contact",
                    ),
                ),
                (
                    "working_hours",
                    models.CharField(
                        blank=True,
                        max_length=100,
                        verbose_name="working hours",
                    ),
                ),
                (
                    "order",
                    models.PositiveIntegerField(
                        default=0,
                        help_text="Display order on contacts page.",
                        verbose_name="order",
                    ),
                ),
                (
                    "is_active",
                    models.BooleanField(default=True, verbose_name="active"),
                ),
            ],
            options={
                "verbose_name": "Contact Person",
                "verbose_name_plural": "Contact Persons",
                "ordering": ["order", "name"],
            },
        ),
    ]
