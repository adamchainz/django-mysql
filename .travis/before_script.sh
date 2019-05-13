#!/bin/bash

set -e
set -x

# DB

# Nuke default
sudo rm -rf /var/lib/mysql

if [[ $DB == 'mysql' ]]
then
    DOCKER_IMAGE="mysql/mysql-server:$DB_VERSION"
    # docker pull "mysql/mysql-server:$DB_VERSION"
    # docker run --name mysql --env MYSQL_ALLOW_EMPTY_PASSWORD=true --env 'MYSQL_ROOT_HOST=%' -p 3306:3306 -d "mysql/mysql-server:$DB_VERSION"
    # set +x
    # until nc 127.0.0.1 3306; do
    #     sleep 0.1
    # done
    # set -x
    # mysql -u root --protocol=TCP -e "
    # SET GLOBAL binlog_format=MIXED;
    # CREATE USER travis@'%' IDENTIFIED BY '';
    # GRANT ALL PRIVILEGES ON *.* TO travis@localhost;"
    # export DB_HOST=127.0.0.1
elif [[ $DB == 'mariadb' ]]
then
    DOCKER_IMAGE="mariadb/server:$DB_VERSION"
else
    echo "unknown DB $DB"
    exit 1
fi

docker pull "$DOCKER_IMAGE"
docker run --name mysql -e MARIADB_ALLOW_EMPTY_PASSWORD=true --env 'MYSQL_ROOT_HOST=%' -p 3306:3306 -d "$DOCKER_IMAGE"
set +x
until nc 127.0.0.1 3306; do
    sleep 0.1
done
set -x
mysql -u root --protocol=TCP -e "
SET GLOBAL binlog_format=MIXED;
CREATE USER travis@'%' IDENTIFIED BY '';
GRANT ALL PRIVILEGES ON *.* TO travis@localhost;"

#     # Install
#     sudo apt-get install -y software-properties-common
#     sudo apt-key adv --recv-keys --keyserver hkp://keyserver.ubuntu.com:80 0xcbcb082a1bb943db
#     sudo add-apt-repository "deb [arch=amd64,i386,ppc64el] http://sfo1.mirrors.digitalocean.com/mariadb/repo/$DB_VERSION/ubuntu xenial main"
#     echo 'Package: *
# Pin: origin sfo1.mirrors.digitalocean.com
# Pin-Priority: 10000' | sudo tee /etc/apt/preferences.d/pin-mariadb.pref
#     sudo apt-get update
#     PACKAGES="mariadb-server mariadb-client"
#     if [[ $DB_VERSION < '10.2' ]]
#     then
#         PACKAGES="$PACKAGES libmariadbclient-dev"
#     fi
#     # shellcheck disable=SC2086
#     sudo DEBIAN_FRONTEND=noninteractive apt-get install -y $PACKAGES

# sudo mysql -u root -e "set global binlog_format=MIXED"

# sudo mysql -u root -e "create user travis@localhost identified by '';" || true

# sudo mysql -u root -e 'grant all privileges on *.* to travis@localhost;'

# percona-toolkit - use non-apt version to avoid mysql package conflicts
# is way out of date
sudo apt-get update -qq
sudo apt-get install -y percona-toolkit
