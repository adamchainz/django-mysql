# -*- encoding:utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import six
from django.db.models import CharField
from django.utils.translation import ugettext_lazy as _

from django_mysql.compat import field_class

from _mysql import escape_string  # isort:skip


class EnumField(field_class(CharField)):
    description = _("MySQL ENUM Type")

    def __init__(self, *args, **kwargs):
        if 'choices' not in kwargs or len(kwargs['choices']) == 0:
            raise ValueError(
                '"choices" argument must be be a non-empty list'
            )

        choices = []
        for choice in kwargs['choices']:
            if isinstance(choice, tuple):
                choices.append(choice)
            elif isinstance(choice, six.string_types):
                choices.append((choice, choice))
            else:
                raise TypeError(
                    'Invalid choice "{choice}". '
                    'Expected string or tuple as elements in choices'.format(
                        choice=choice,
                    )
                )

        kwargs['choices'] = choices
        super(EnumField, self).__init__(*args, **kwargs)

    def _check_max_length_attribute(self, **kwargs):
        # Disable max length check on Django 1.7
        return []

    def deconstruct(self):
        name, path, args, kwargs = super(EnumField, self).deconstruct()
        bad_paths = (
            'django_mysql.models.fields.enum.' + self.__class__.__name__,
            'django_mysql.models.fields.' + self.__class__.__name__
        )
        if path in bad_paths:
            path = 'django_mysql.models.' + self.__class__.__name__

        kwargs['choices'] = self.choices
        return name, path, args, kwargs

    def db_type(self, connection):
        values = [escape_string(c) for c, _ in self.flatchoices]
        return 'enum(%s)' % ','.join(
            "'%s'" % v.decode('utf8') for v in values
        )
