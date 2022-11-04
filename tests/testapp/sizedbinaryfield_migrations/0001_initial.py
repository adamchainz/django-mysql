from __future__ import annotations

from django.db import migrations
from django.db import models

from django_mysql.models import SizedBinaryField


class Migration(migrations.Migration):

    dependencies: list[tuple[str, str]] = []

    operations = [
        migrations.CreateModel(
            name="SizedBinaryAlterModel",
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
                ("field", SizedBinaryField(size_class=4)),
            ],
            options={},
            bases=(models.Model,),
        )
    ]
