from django.db import migrations, models

from django_mysql import models as mysql_models


class Migration(migrations.Migration):

    dependencies = []
    operations = [
        migrations.AlterField(
            model_name='modifiabledatetimemodel',
            name='field_4',
            field=models.DateTimeField(),
        ),
    ]
