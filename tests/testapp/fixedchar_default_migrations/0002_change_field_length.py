from __future__ import annotations

from django.db import migrations

from django_mysql.models import FixedCharField


class Migration(migrations.Migration):

    dependencies = [("testapp", "0001_initial")]

    operations = [
        migrations.AlterField(
            model_name="FixedCharDefaultModel",
            name="zip_code",
            field=FixedCharField(max_length=10),
        )
    ]
