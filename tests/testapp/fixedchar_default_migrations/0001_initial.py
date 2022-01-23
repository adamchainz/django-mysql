from __future__ import annotations

from typing import List, Tuple

from django.db import migrations, models

from django_mysql.models import FixedCharField


class Migration(migrations.Migration):

    dependencies: List[Tuple[str, str]] = []

    operations = [
        migrations.CreateModel(
            name="FixedCharDefaultModel",
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
                    "zip_code",
                    FixedCharField(length=5),
                ),
            ],
            options={},
            bases=(models.Model,),
        )
    ]
