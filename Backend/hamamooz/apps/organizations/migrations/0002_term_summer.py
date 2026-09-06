from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("organizations", "0001_initial")]

    operations = [
        migrations.AlterField(
            model_name="term",
            name="code",
            field=models.CharField(
                choices=[
                    ("summer", "تابستان"),
                    ("first", "نوبت اول"),
                    ("second", "نوبت دوم"),
                ],
                max_length=20,
            ),
        ),
    ]
