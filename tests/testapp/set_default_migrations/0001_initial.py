from typing import List, Tuple

from django.db import migrations, models

from django_mysql.models import SetCharField


class Migration(migrations.Migration):

    dependencies: List[Tuple[str, str]] = []

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
