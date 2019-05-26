#!/bin/sh
set -ex
export CUSTOM_COMPILE_COMMAND="./requirements-compile.sh"
# mysqlclient requirements found on each version's "Databases" documentation page:
# https://docs.djangoproject.com/en/2.2/ref/databases/#id6
python3.5 -m piptools compile -P 'Django>=1.11,<2.0' -P 'mysqlclient>=1.3.3,<=1.3.13' "$@" -o requirements/py35-django111.txt
python3.5 -m piptools compile -P 'Django>=2.0,<2.1' -P 'mysqlclient>=1.3.7,<=1.3.13' "$@" -o requirements/py35-django20.txt
python3.5 -m piptools compile -P 'Django>=2.1,<2.2' -P 'mysqlclient>=1.3.7' "$@" -o requirements/py35-django21.txt
python3.5 -m piptools compile -P 'Django>=2.2,<2.3' -P 'mysqlclient>=1.3.13' "$@" -o requirements/py35-django22.txt
python3.6 -m piptools compile -P 'Django>=1.11,<2.0' -P 'mysqlclient>=1.3.3,<=1.3.13' "$@" -o requirements/py36-django111.txt
python3.6 -m piptools compile -P 'Django>=2.0,<2.1' -P 'mysqlclient>=1.3.7,<=1.3.13' "$@" -o requirements/py36-django20.txt
python3.6 -m piptools compile -P 'Django>=2.1,<2.2' -P 'mysqlclient>=1.3.7' "$@" -o requirements/py36-django21.txt
python3.6 -m piptools compile -P 'Django>=2.2,<2.3' -P 'mysqlclient>=1.3.13' "$@" -o requirements/py36-django22.txt
python3.7 -m piptools compile -P 'Django>=1.11,<2.0' -P 'mysqlclient>=1.3.3,<=1.3.13' "$@" -o requirements/py37-django111.txt
python3.7 -m piptools compile -P 'Django>=2.0,<2.1' -P 'mysqlclient>=1.3.7,<=1.3.13' "$@" -o requirements/py37-django20.txt
python3.7 -m piptools compile -P 'Django>=2.1,<2.2' -P 'mysqlclient>=1.3.7' "$@" -o requirements/py37-django21.txt
python3.7 -m piptools compile -P 'Django>=2.2,<2.3' -P 'mysqlclient>=1.3.13' "$@" -o requirements/py37-django22.txt
