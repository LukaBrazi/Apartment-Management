# No-op: this slot was created when the help_text on
# ``Rating.organization`` was tightened.  The change has since been
# folded into 0002_rating_organization.py, so this migration runs
# zero operations.  Left as an empty placeholder to preserve the
# migration sequence on environments that already applied 0003 from
# an earlier dev run.
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("ratings", "0002_rating_organization"),
    ]

    operations = []
