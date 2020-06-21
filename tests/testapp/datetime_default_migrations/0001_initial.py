from django.db import migrations, models

import django.utils.timezone

from django_mysql.models import DateTimeField


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
                ("datetime1", DateTimeField(on_update_current_timestamp=True)),
                ("datetime2", DateTimeField(auto_now=True)),
                ("datetime3", DateTimeField(default=django.utils.timezone.now)),
            ],
        ),
    ]
