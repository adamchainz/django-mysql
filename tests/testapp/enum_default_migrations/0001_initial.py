from typing import List, Tuple

from django.db import migrations, models

from django_mysql.models import EnumField


class Migration(migrations.Migration):

    dependencies: List[Tuple[str, str]] = []

    operations = [
        migrations.CreateModel(
            name="EnumDefaultModel",
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
                    EnumField(choices=[("lion", "Lion"), ("tiger", "Tiger"), "bear"]),
                ),
            ],
            options={},
            bases=(models.Model,),
        )
    ]
