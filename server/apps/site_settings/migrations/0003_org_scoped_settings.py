# Migration: Link SiteSettings and ContactPerson to Organization
# SiteSettings goes from singleton (pk=1) to per-organization model.
# organization=NULL = platform default settings (fallback).

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("site_settings", "0002_whitelabel_branding_and_contacts"),
        ("organizations", "0001_initial"),
    ]

    operations = [
        # SiteSettings → OneToOneField to Organization (nullable = platform default)
        migrations.AddField(
            model_name="sitesettings",
            name="organization",
            field=models.OneToOneField(
                blank=True,
                help_text="NULL = platform default settings",
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="site_settings",
                to="organizations.organization",
            ),
        ),
        # ContactPerson → ForeignKey to Organization (nullable = platform-level contact)
        migrations.AddField(
            model_name="contactperson",
            name="organization",
            field=models.ForeignKey(
                blank=True,
                help_text="NULL = platform-level contact",
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="contact_persons",
                to="organizations.organization",
            ),
        ),
    ]
