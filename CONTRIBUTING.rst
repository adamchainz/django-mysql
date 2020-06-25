============
Contributing
============

Contributions are welcome, and they are greatly appreciated! Every little bit
helps, and credit will always be given.

You can contribute in many ways:

Types of Contributions
----------------------

Report Bugs
~~~~~~~~~~~

Report bugs via `Github Issues
<https://github.com/adamchainz/django-mysql/issues>`_.

If you are reporting a bug, please include:

* Your versions of Django-MySQL, Django, and MySQL/MariaDB
* Any other details about your local setup that might be helpful in
  troubleshooting, e.g. operating system.
* Detailed steps to reproduce the bug.

Fix Bugs
~~~~~~~~

Look through the GitHub issues for bugs. Anything tagged with "bug"
is open to whoever wants to implement it.

Implement Features
~~~~~~~~~~~~~~~~~~

Look through the GitHub issues for features. Anything tagged with "help wanted"
and not assigned to anyone is open to whoever wants to implement it - please
leave a comment to say you have started working on it, and open a pull request
as soon as you have something working, so that Travis starts building it.

Issues without "help wanted" generally already have some code ready in the
background (maybe it's not yet open source), but you can still contribute to
them by saying how you'd find the fix useful, linking to known prior art, or
other such help.

Write Documentation
~~~~~~~~~~~~~~~~~~~

Django-MySQL could always use more documentation, whether as part of the
official Django-MySQL docs, in docstrings, or even on the web in blog posts,
articles, and such. Write away!

Submit Feedback
~~~~~~~~~~~~~~~

The best way to send feedback is to file an issue via `Github Issues
<https://github.com/adamchainz/django-mysql/issues>`_.

If you are proposing a feature:

* Explain in detail how it would work.
* Keep the scope as narrow as possible, to make it easier to implement.
* Remember that this is a volunteer-driven project, and that contributions
  are welcome :)
* Link to any prior art, e.g. MySQL/MariaDB documentation that details the
  necessary database features

Get Started!
------------

Ready to contribute? Here's how to set up Django-MySQL for local development.

1. Fork the Django-MySQL repo on GitHub.
2. Clone your fork locally:

   .. code-block:: sh

       $ git clone git@github.com:your_name_here/django-mysql.git
       $ cd django-mysql/

3. Check you have a supported version of MySQL or MariaDB running and that the
   settings in ``tests/settings.py`` will work for connecting. This involves
   making sure you can connect from your terminal with the plain command
   ``mysql`` with no options, i.e. as your current user.

   On Ubuntu, this can be done with the commands below:

   .. code-block:: sh

       $ sudo apt-get install mysql-server-5.7
       $ mysql -uroot -p -e "CREATE USER '$(whoami)'@localhost; GRANT ALL PRIVILEGES ON *.* TO '$(whoami)'@localhost;"
       # Enter the password for root you set in the apt dialog

   On Mac OS X, this can be done with something like:

   .. code-block:: sh

       $ brew install mariadb
       $ mysql.server start
       $ mysql -uroot -e "CREATE USER '$(whoami)'@localhost; GRANT ALL PRIVILEGES ON *.* TO '$(whoami)'@localhost;"

   If you want to use a different user or add a password, you can patch the
   settings file in your local install.

5. Install ``tox`` and run the tests for Python 3.8 + Django 3.0:

   .. code-block:: sh

       $ python -m pip install tox
       $ tox -e py38-django30

   The ``tox.ini`` file defines a large number of test environments, for
   different Python and Django versions, plus for checking codestyle. During
   development of a feature/fix, you'll probably want to run just one plus the
   relevant codestyle:

   .. code-block:: sh

       $ tox -e py38-codestyle,py38-django30

   You can run all the environments to check your code is okay for them with:

   .. code-block:: sh

       $ tox

6. To make changes, create a branch for local development:

   .. code-block:: sh

       $ git checkout -b name-of-your-bugfix-or-feature

   ...and hack away!

7. Commit your changes and push your branch to GitHub:

   .. code-block:: sh

       $ git add .
       $ git commit -m "Your detailed description of your changes."
       $ git push origin name-of-your-bugfix-or-feature

8. Submit a pull request through the GitHub website. This will trigger the
   Travis build which runs the tests against all supported versions of Python,
   Django, and MySQL/MariaDB.

Testing Tips
------------

To only run a particular test file, you can run with the path to that file:

.. code-block:: sh

    $ tox -- tests/testapp/test_some_feature.py

You can also pass other pytest arguments through ``tox`` after the ``--``
separator. There are lots of other useful features, most of which you can check
out in the `pytest docs <http://docs.pytest.org/en/latest/>`_!
