from __future__ import annotations

from django.db import migrations, models

from django_mysql.models import PositiveTinyIntegerField, TinyIntegerField


class Migration(migrations.Migration):
    dependencies: list[tuple[str, str]] = []

    operations = [
        migrations.CreateModel(
            name="TinyIntegerDefaultModel",
            fields=[
                (
                    "id",
                    models.AutoField(
                        verbose_name="ID",
                        serialize=False,
                        auto_created=True,
                        primary_key=True,
                    ),
                ),
                (
                    "tiny_signed",
                    PositiveTinyIntegerField(),
                ),
                (
                    "tiny_unsigned",
                    TinyIntegerField(),
                ),
            ],
            options={},
            bases=(models.Model,),
        )
    ]
