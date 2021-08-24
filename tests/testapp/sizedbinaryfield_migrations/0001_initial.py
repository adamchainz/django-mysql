from typing import List, Tuple

from django.db import migrations, models

from django_mysql.models import SizedBinaryField


class Migration(migrations.Migration):

    dependencies: List[Tuple[str, str]] = []

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
