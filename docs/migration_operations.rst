.. _migration_operations:

====================
Migration Operations
====================

.. currentmodule:: django_mysql.models.operations

MySQL-specific `migration operations
<https://docs.djangoproject.com/en/dev/ref/migration-operations/>`_
that can all be imported from ``django_mysql.operations``.


Install Plugin
--------------

.. class:: InstallPlugin(name, soname)

    An ``Operation`` subclass that installs a MySQL plugin. Runs
    ``INSTALL PLUGIN name SONAME soname``, but does a check to see if the
    plugin is already installed to make it more idempotent.

    Docs:
    `MySQL <https://dev.mysql.com/doc/refman/5.5/en/install-plugin.html>`_ /
    `MariaDB <https://mariadb.com/kb/en/mariadb/install-plugin/>`_.

    .. attribute:: name

        This is a required argument. The name of the plugin to install.

    .. attribute:: soname

        This is a required argument. The name of the library to install the
        plugin from. Note that on MySQL you must include the extension (e.g.
        ``.so``, ``.dll``) whilst on MariaDB you may skip it to keep the
        operation platform-independent.

    Example usage::

        # -*- coding: utf-8 -*-
        from __future__ import unicode_literals

        from django.db import migrations

        from django_mysql.operations import InstallPlugin


        class Migration(migrations.Migration):

            dependencies = [
            ]

            operations = [
                # Install https://mariadb.com/kb/en/mariadb/metadata_lock_info/
                InstallPlugin("metadata_lock_info", "metadata_lock_info.so")
            ]



Install SOName
--------------

.. class:: InstallSOName(soname)

    **MariaDB** only.

    An ``Operation`` subclass that installs a MariaDB plugin library. One
    library may contain multiple plugins that work together, this installs all
    of the plugins in the named library file. Runs ``INSTALL SONAME soname``.
    Note that unlike ``InstallPlugin``, there is no idempotency check to see if
    the library is already installed, since there is no way of knowing if all
    the plugins inside the library are installed.

    Docs: `MariaDB <https://mariadb.com/kb/en/mariadb/install-soname/>`_.

    .. attribute:: soname

        This is a required argument. The name of the library to install the
        plugin from. You may skip the file extension (e.g. ``.so``, ``.dll``)
        to keep the operation platform-independent.

    Example usage::

        # -*- coding: utf-8 -*-
        from __future__ import unicode_literals

        from django.db import migrations

        from django_mysql.operations import InstallSOName


        class Migration(migrations.Migration):

            dependencies = [
            ]

            operations = [
                # Install https://mariadb.com/kb/en/mariadb/metadata_lock_info/
                InstallSOName("metadata_lock_info")
            ]
