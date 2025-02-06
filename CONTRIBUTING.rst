============
Contributing
============

Run the tests
-------------

1. Install `tox <https://tox.wiki/en/latest/>`__.

2. Run a supported version of MySQL or MariaDB.
   This is easiest with the official Docker images.
   For example:

   .. code-block:: console

      docker run --detach --name mariadb -e MYSQL_ROOT_PASSWORD=hunter2 --publish 3306:3306 mariadb:11.6

3. Run the tests by passing environment variables with your connection parameters.
   For the above Docker command:

   .. code-block:: console

      DB_HOST=127.0.0.1 DB_USER=root DB_PASSWORD='hunter2' tox -e py313-django51

  tox environments are split per Python and Django version.

  You can run a subset of tests by passing them after ``--`` like:

  .. code-block:: console

    DB_HOST=127.0.0.1 DB_USER=root DB_PASSWORD='hunter2' tox -e py313-django51 -- tests/testapp/test_cache.py

  You can also pass other pytest arguments after the ``--``.

4. When you’re done, shut down the Docker container with:

   .. code-block:: console

      docker rm --force mariadb
