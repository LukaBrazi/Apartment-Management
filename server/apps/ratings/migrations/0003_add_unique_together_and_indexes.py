from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ratings", "0002_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name="rating",
            unique_together={("rating_user", "rated_user")},
        ),
        migrations.AddIndex(
            model_name="rating",
            index=models.Index(fields=["rated_user"], name="rating_rated_user_idx"),
        ),
        migrations.AddIndex(
            model_name="rating",
            index=models.Index(fields=["rating_user"], name="rating_rating_user_idx"),
        ),
    ]
