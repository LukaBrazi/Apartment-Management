# Generated migration for Organization models

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Organization',
            fields=[
                ('pkid', models.BigAutoField(editable=False, primary_key=True, serialize=False)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created At')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Updated At')),
                ('name', models.CharField(max_length=255, verbose_name='Organization Name')),
                ('slug', models.SlugField(max_length=255, unique=True, verbose_name='Slug')),
                ('type', models.CharField(choices=[('housing_complex', 'Житловий комплекс'), ('cottage_village', 'Котеджне село'), ('management_company', 'Управляюча компанія')], default='housing_complex', max_length=30, verbose_name='Organization Type')),
                ('features', models.JSONField(default=dict, help_text='Feature flags for this organization', verbose_name='Features')),
                ('address', models.CharField(blank=True, default='', max_length=500, verbose_name='Address')),
                ('city', models.CharField(blank=True, default='', max_length=100, verbose_name='City')),
                ('description', models.TextField(blank=True, default='', verbose_name='Description')),
                ('phone', models.CharField(blank=True, default='', max_length=20, verbose_name='Phone')),
                ('email', models.EmailField(blank=True, default='', max_length=254, verbose_name='Email')),
                ('is_active', models.BooleanField(db_index=True, default=True, verbose_name='Active')),
                ('owner', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='owned_organizations', to=settings.AUTH_USER_MODEL, verbose_name='Owner')),
            ],
            options={
                'verbose_name': 'Organization',
                'verbose_name_plural': 'Organizations',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='OrganizationMembership',
            fields=[
                ('pkid', models.BigAutoField(editable=False, primary_key=True, serialize=False)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created At')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Updated At')),
                ('role', models.CharField(choices=[('super_admin', 'Суперадміністратор'), ('director', 'Директор'), ('admin', 'Адміністратор'), ('staff', 'Персонал'), ('resident', 'Мешканець')], default='resident', max_length=30, verbose_name='Role')),
                ('is_active', models.BooleanField(db_index=True, default=True, verbose_name='Active')),
                ('staff_type', models.CharField(blank=True, default='', help_text='Type of staff (e.g., electrician, plumber)', max_length=100, verbose_name='Staff Type')),
                ('joined_at', models.DateTimeField(auto_now_add=True, verbose_name='Joined At')),
                ('invited_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='sent_org_invitations', to=settings.AUTH_USER_MODEL, verbose_name='Invited By')),
                ('organization', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='memberships', to='organizations.organization', verbose_name='Organization')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='organization_memberships', to=settings.AUTH_USER_MODEL, verbose_name='User')),
            ],
            options={
                'verbose_name': 'Organization Membership',
                'verbose_name_plural': 'Organization Memberships',
                'ordering': ['-created_at'],
                'unique_together': {('user', 'organization')},
            },
        ),
    ]
