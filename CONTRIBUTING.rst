============
Contributing
============

Run the tests
-------------

1. Install `tox <https://tox.wiki/en/latest/>`__ and ensure Docker is running.

2. Run the tests:

   .. code-block:: console

      tox -e py314-django61

   By default this uses the ``mariadb:11.4`` image.
   To use a different image, set ``DB_IMAGE``:

   .. code-block:: console

      DB_IMAGE=mysql:8.4 tox -e py314-django61

   tox environments are split per Python and Django version.

   You can run a subset of tests by passing them after ``--`` like:

   .. code-block:: console

      tox -e py314-django61 -- tests/testapp/test_cache.py

   You can also pass other pytest arguments after the ``--``.
