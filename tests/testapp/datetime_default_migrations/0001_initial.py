from django.db import migrations, models

from django_mysql import models as mysql_models


class Migration(migrations.Migration):

    dependencies = []
    operations = [
        migrations.CreateModel(
            name="ModifiableDatetimeModel",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("model_char", models.CharField(default="", max_length=16)),
                ("on_update_datetime_to_be_altered_field", models.DateTimeField()),
                (
                    "on_update_datetime_false_field",
                    mysql_models.DatetimeField(on_update_current_timestamp=True),
                ),
                (
                    "on_update_datetime_auto_now_field",
                    mysql_models.DatetimeField(
                        auto_now=True, on_update_current_timestamp=True
                    ),
                ),
            ],
        ),
    ]
