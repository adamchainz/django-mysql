# -*- coding:utf-8 -*-
from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class MySQLConfig(AppConfig):
    name = 'django_mysql'
    verbose_name = _('MySQL extensions')

    def ready(self):
        self.perform_monkey_patches()
        self.add_lookups()

    def perform_monkey_patches(self):
        from django.db.backends.mysql.base import DatabaseWrapper
        from django_mysql.monkey_patches import is_mariadb

        # Fine to patch straight on since it's a cached_property descriptor
        DatabaseWrapper.is_mariadb = is_mariadb

    def add_lookups(self):
        from django.db.models import CharField, TextField
        from django_mysql.models.lookups import Soundex, SoundsLike

        CharField.register_lookup(SoundsLike)
        CharField.register_lookup(Soundex)
        TextField.register_lookup(SoundsLike)
        TextField.register_lookup(Soundex)
