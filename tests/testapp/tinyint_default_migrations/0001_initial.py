from __future__ import annotations

from django.db import migrations, models

from django_mysql.models import PositiveTinyIntegerField, TinyIntegerField


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
                    "discount_amt",
                    TinyIntegerField(),
                ),
                (
                    "discount_amt_pct",
                    PositiveTinyIntegerField(),
                ),
            ],
            options={},
            bases=(models.Model,),
        )
    ]
