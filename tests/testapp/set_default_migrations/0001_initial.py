from __future__ import annotations

from django.db import migrations
from django.db import models

from django_mysql.models import SetCharField


class Migration(migrations.Migration):
    dependencies: list[tuple[str, str]] = []

    operations = [
        migrations.CreateModel(
            name="IntSetDefaultModel",
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
                    "field",
                    SetCharField(models.IntegerField(), size=None, max_length=32),
                ),
            ],
            options={},
            bases=(models.Model,),
        )
    ]
