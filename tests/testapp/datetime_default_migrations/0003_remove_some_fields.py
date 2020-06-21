from django.db import migrations, models

from django_mysql import models as mysql_models


class Migration(migrations.Migration):

    dependencies = [("testapp", "0002_add_some_fields")]
    operations = [
        migrations.AlterField(
            model_name='DatetimeModel',
            name='datetime4',
            field=models.DateTimeField(),
        ),
    ]
