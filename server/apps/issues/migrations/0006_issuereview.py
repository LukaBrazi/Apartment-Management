import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("issues", "0005_alter_issue_status"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="IssueReview",
            fields=[
                (
                    "pkid",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False
                    ),
                ),
                (
                    "id",
                    models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "rating",
                    models.IntegerField(
                        choices=[
                            (1, "1 — Дуже погано"),
                            (2, "2 — Погано"),
                            (3, "3 — Задовільно"),
                            (4, "4 — Добре"),
                            (5, "5 — Відмінно"),
                        ],
                        verbose_name="Rating",
                    ),
                ),
                ("comment", models.TextField(blank=True, verbose_name="Comment")),
                (
                    "issue",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="reviews",
                        to="issues.issue",
                        verbose_name="Issue",
                    ),
                ),
                (
                    "reviewer",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="issue_reviews_given",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Reviewer",
                    ),
                ),
                (
                    "reviewee",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="issue_reviews_received",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Reviewee",
                    ),
                ),
            ],
            options={
                "verbose_name": "Issue Review",
                "verbose_name_plural": "Issue Reviews",
                "unique_together": {("issue", "reviewer")},
            },
        ),
    ]
