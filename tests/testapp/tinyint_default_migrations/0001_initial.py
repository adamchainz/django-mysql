from __future__ import annotations

from django.db import migrations, models

from django_mysql.models import TinyIntegerField, PositiveTinyIntegerField


class Migration(migrations.Migration):

    dependencies: list[tuple[str, str]] = []

    operations = [
        migrations.CreateModel(
            name="TinyIntDefaultModel",
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
                    "col1",
                    TinyIntegerField(),
                ),
                (
                    "col2",
                    PositiveTinyIntegerField(),
                ),
            ],
            options={},
            bases=(models.Model,),
        )
    ]
