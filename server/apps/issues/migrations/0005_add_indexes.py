from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("issues", "0004_add_category_due_at_status_extended"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="issue",
            index=models.Index(fields=["status"], name="issue_status_idx"),
        ),
        migrations.AddIndex(
            model_name="issue",
            index=models.Index(fields=["priority"], name="issue_priority_idx"),
        ),
        migrations.AddIndex(
            model_name="issue",
            index=models.Index(fields=["status", "priority"], name="issue_status_priority_idx"),
        ),
        migrations.AddIndex(
            model_name="issue",
            index=models.Index(fields=["reported_by", "status"], name="issue_reporter_status_idx"),
        ),
        migrations.AddIndex(
            model_name="issue",
            index=models.Index(fields=["assigned_to", "status"], name="issue_assignee_status_idx"),
        ),
        migrations.AddIndex(
            model_name="category",
            index=models.Index(fields=["name"], name="category_name_idx"),
        ),
    ]
