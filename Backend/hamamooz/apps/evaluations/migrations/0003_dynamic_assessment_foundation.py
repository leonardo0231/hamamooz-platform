from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Foundation migration for dynamic assessment architecture.

    The concrete database migration of dynamic models will be generated after
    the models are registered in Django app models.py. This placeholder keeps
    migration history explicit during the transition from monthly-only data.
    """

    dependencies = [
        ("evaluations", "0002_alter_monthlyevaluation_framework_version"),
    ]

    operations = []
