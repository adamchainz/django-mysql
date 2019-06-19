from django.db import migrations

from django_mysql.models import SizedTextField


class Migration(migrations.Migration):

    dependencies = [("testapp", "0001_initial")]

    operations = [
        migrations.AlterField(
            model_name="sizedtextaltermodel",
            name="field",
            field=SizedTextField(size_class=1),
        )
    ]
