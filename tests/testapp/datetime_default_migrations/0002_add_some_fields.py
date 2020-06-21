from django.db import migrations, models

from django_mysql import models as mysql_models
from django_mysql.models import DateTimeField


class Migration(migrations.Migration):

    dependencies = []
    operations = [
        migrations.AddField(
            model_name='modifiabledatetimemodel',
            name='datetime4',
            field=DateTimeField(on_update_current_timestamp=True),
        ),
    ]
