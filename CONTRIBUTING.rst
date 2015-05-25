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
2. Clone your fork locally::

    $ git clone git@github.com:your_name_here/django-mysql.git
    $ cd django-mysql/

3. Install your local copy into a virtualenv. Assuming you have
   ``virtualenvwrapper`` installed, this is how you set up your fork for local
   development::

    $ mkvirtualenv django-mysql
    $ pip install -r requirements.txt

4. Check you have MySQL/MariaDB running and that the settings in
   ``tests/settings.py`` will work for connecting. Then run the tests with::

    $ ./runtests.py

   To test every version of Python and Django, make sure you have ``tox``
   installed globally (outside of your virtualenv), then run::

    $ tox

5. Now to make changes, create a branch for local development::

    $ git checkout -b name-of-your-bugfix-or-feature

   And hack away!

6. When you're done making changes, check that your changes pass the code style
   rules and the tests on all versions of Python and Django, by running tox::

    $ tox

   If it's too tricky setting up multiple versions of Python, don't worry about
   it - it will be picked up by the Travis build from Github. As long as
   ``runtests`` passes, you have a good start.

6. Commit your changes and push your branch to GitHub::

    $ git add .
    $ git commit -m "Your detailed description of your changes."
    $ git push origin name-of-your-bugfix-or-feature

7. Submit a pull request through the GitHub website. This will trigger the
   Travis build which runs the tests against all supported versions of Python,
   Django, and MySQL/MariaDB.


Pull Request Guidelines
-----------------------

Before you submit a pull request, check that it meets these guidelines:

1. The pull request should include tests.
2. If the pull request adds functionality, the docs should be updated. Put
   your new functionality into a function with a docstring, and add the
   feature to the list in README.rst.
3. The pull request should pass on Travis - it automatically gains a "check"
   link from Github which we're hoping turns green :)

Tips
----

Tests use pytest. You can run a subset of tests with::

    $ ./runtests.py -k test_pattern

Or::

    $ tox -- -k test_pattern

For other switches, see the pytest docs.
