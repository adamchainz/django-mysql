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

3. Install your local copy into a virtualenv. Assuming you have
   ``virtualenvwrapper`` installed, this is how you set up your fork for local
   development:

   .. code-block:: sh

       $ mkvirtualenv django-mysql
       $ pip install -r requirements.txt

4. Check you have MySQL or MariaDB running and that the settings in
   ``tests/settings.py`` will work for connecting. This involves making sure
   you can connect from your terminal with the plain command ``mysql``, i.e.
   as your current user.

   On Ubuntu, this can be done with the commands below:

   .. code-block:: sh

       $ sudo apt-get install mysql-server-5.6
       $ mysql -uroot -p -e "CREATE USER '$(whoami)'@localhost; GRANT ALL PRIVILEGES ON *.* TO '$(whoami)'@localhost;"
       # Enter the password for root you set in the apt dialog

   On Max OS X, this can be done with something like:

   .. code-block:: sh

       $ brew install mariadb
       $ mysql.server start
       $ mysql -uroot -e "GRANT ALL PRIVILEGES ON *.* TO ''@localhost;"

   If you want to use a different user or add a password, you can patch the
   settings file in your local install.

5. Then run the tests with:

   .. code-block:: sh

       $ ./runtests.py

   To test every version of Python and Django, make sure you have ``tox``
   installed globally (outside of your virtualenv), then run:

   .. code-block:: sh

       $ tox

6. Now to make changes, create a branch for local development:

   .. code-block:: sh

       $ git checkout -b name-of-your-bugfix-or-feature

   And hack away!

7. When you're done making changes, check that your changes pass the code style
   rules and the tests on all versions of Python and Django, by running tox:

   .. code-block:: sh

       $ tox

   If it's too tricky setting up multiple versions of Python, don't worry about
   it - it will be picked up by the Travis build from Github. As long as
   ``runtests`` passes, you have a good start.

8. Commit your changes and push your branch to GitHub:

   .. code-block:: sh

       $ git add .
       $ git commit -m "Your detailed description of your changes."
       $ git push origin name-of-your-bugfix-or-feature

9. Submit a pull request through the GitHub website. This will trigger the
   Travis build which runs the tests against all supported versions of Python,
   Django, and MySQL/MariaDB.


Pull Request Checklist
----------------------

When you open a Pull Request on Github, a checklist will be pre-populated in
the message. Please check all of the steps have been done, or ask for
assistance in doing so!

Testing Tips
------------

The tests do a lot of work that you can reduce by using some features that are
available.

To skip the linting phase, run them with:

.. code-block:: sh

    $ ./runtests.py --nolint

To only run a particular test file, you can run with the path to that file:

.. code-block:: sh

    $ ./runtests.py tests/testapp/test_some_feature.py

You can also pass arguments through ``tox`` to ``runtests.py`` by passing these
arguments after the ``--`` separator, for example:

.. code-block:: sh

    $ tox -- tests/testapp/test_some_feature.py

There are lots of other useful features, most of which you can check out in the
`pytest docs <http://pytest.org/latest/>`_!
