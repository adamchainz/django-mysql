# -*- coding:utf-8 -*-
from django.apps import AppConfig
from django.db.models import CharField, TextField
from django.utils.translation import ugettext_lazy as _

from .lookups import Soundex, SoundsLike


class MySQLConfig(AppConfig):
    name = 'django_mysql'
    verbose_name = _('MySQL extensions')

    def ready(self):
        CharField.register_lookup(SoundsLike)
        CharField.register_lookup(Soundex)
        TextField.register_lookup(SoundsLike)
        TextField.register_lookup(Soundex)
