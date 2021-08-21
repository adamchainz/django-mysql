from typing import List, Tuple

from django.db import migrations, models

from django_mysql.models import SizedTextField


class Migration(migrations.Migration):

    dependencies: List[Tuple[str, str]] = []

    operations = [
        migrations.CreateModel(
            name="SizedTextAlterModel",
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
                ("field", SizedTextField(size_class=3)),
            ],
            options={},
            bases=(models.Model,),
        )
    ]
