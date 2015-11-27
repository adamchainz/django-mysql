# -*- coding:utf-8 -*-
from django.apps import AppConfig
from django.conf import settings
from django.utils.translation import ugettext_lazy as _

from .checks import register_checks


class MySQLConfig(AppConfig):
    name = 'django_mysql'
    verbose_name = _('MySQL extensions')

    def ready(self):
        self.perform_monkey_patches()
        self.add_lookups()
        register_checks()

    def perform_monkey_patches(self):
        from django.db.backends.mysql.base import DatabaseWrapper
        from django_mysql import monkey_patches

        # Fine to patch straight on since it's a cached_property descriptor
        DatabaseWrapper.is_mariadb = monkey_patches.is_mariadb

        # Depends on setting
        if getattr(settings, 'DJANGO_MYSQL_REWRITE_QUERIES', False):
            monkey_patches.patch_CursorWrapper_execute()

    def add_lookups(self):
        from django.db.models import CharField, TextField
        from django_mysql.models.lookups import (
            CaseSensitiveExact, Soundex, SoundsLike
        )

        CharField.register_lookup(CaseSensitiveExact)
        CharField.register_lookup(SoundsLike)
        CharField.register_lookup(Soundex)
        TextField.register_lookup(CaseSensitiveExact)
        TextField.register_lookup(SoundsLike)
        TextField.register_lookup(Soundex)
