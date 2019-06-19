from django.db import migrations

from django_mysql.models import EnumField


class Migration(migrations.Migration):

    dependencies = [("testapp", "0001_initial")]

    operations = [
        migrations.AlterField(
            model_name="EnumDefaultModel",
            name="field",
            field=EnumField(
                choices=[
                    ("lion", "Lion"),
                    ("tiger", "Tiger"),
                    ("bear", "Bear"),
                    "oh my!",
                ]
            ),
        )
    ]
