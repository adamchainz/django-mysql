#!/bin/bash

set -e
set -x

# DB

# Install dbdeployer
# VERSION=1.30.0
# OS=linux
# origin=https://github.com/datacharmer/dbdeployer/releases/download/v$VERSION
# wget "$origin/dbdeployer-$VERSION.$OS.tar.gz"
# tar -xzf "dbdeployer-$VERSION.$OS.tar.gz"
# chmod +x "dbdeployer-$VERSION.$OS"
# sudo mv "dbdeployer-$VERSION.$OS" /usr/local/bin/dbdeployer


# Nuke default
sudo rm -rf /var/lib/mysql

if [[ $DB == 'mysql' ]]
then
    docker pull "mysql/mysql-server:$DB_VERSION"
    docker run --name mysql --env MYSQL_ALLOW_EMPTY_PASSWORD=true --env MYSQL_ROOT_PASSWORD= -d "mysql/mysql-server:$DB_VERSION"
    docker exec -it mysql mysql -uroot -e "
    SET GLOBAL binlog_format=MIXED;
    CREATE USER travis@'%' IDENTIFIED BY '';
    GRANT ALL PRIVILEGES ON *.* TO travis@localhost;
    "
    export DB_HOST=127.0.0.1 DB_USER=travis

#     dbdeployer remote download mysql-5.6.44
#     mkdir -p /root/opt/mysql
#     dbdeployer unpack mysql-5.6.44.tar.xz
#     dbdeployer deploy single 5.6

#     # Install new
#     sudo wget https://dev.mysql.com/get/mysql-apt-config_0.8.13-1_all.deb
#     sudo dpkg -i mysql-apt-config_0.8.13-1_all.deb
#     sudo add-apt-repository "deb http://repo.mysql.com/apt/ubuntu/ xenial mysql-$DB_VERSION"
#     sudo cat .travis/oracle.pgp-key | sudo apt-key add -
#     sudo apt-get update
#     echo 'Package: *
# Pin: origin repo.mysql.com
# Pin-Priority: 10000' | sudo tee /etc/apt/preferences.d/pin-mysql.pref
#     sudo DEBIAN_FRONTEND=noninteractive apt-get install -y "mysql-$DB_VERSION"
elif [[ $DB == 'mariadb' ]]
then
    # Install
    sudo apt-get install -y software-properties-common
    sudo apt-key adv --recv-keys --keyserver hkp://keyserver.ubuntu.com:80 0xcbcb082a1bb943db
    sudo add-apt-repository "deb [arch=amd64,i386,ppc64el] http://sfo1.mirrors.digitalocean.com/mariadb/repo/$DB_VERSION/ubuntu xenial main"
    echo 'Package: *
Pin: origin sfo1.mirrors.digitalocean.com
Pin-Priority: 10000' | sudo tee /etc/apt/preferences.d/pin-mariadb.pref
    sudo apt-get update
    PACKAGES="mariadb-server mariadb-client"
    if [[ $DB_VERSION < '10.2' ]]
    then
        PACKAGES="$PACKAGES libmariadbclient-dev"
    fi
    # shellcheck disable=SC2086
    sudo DEBIAN_FRONTEND=noninteractive apt-get install -y $PACKAGES
fi

# sudo mysql -u root -e "set global binlog_format=MIXED"

# sudo mysql -u root -e "create user travis@localhost identified by '';" || true

# sudo mysql -u root -e 'grant all privileges on *.* to travis@localhost;'

# percona-toolkit - use non-apt version to avoid mysql package conflicts
# is way out of date
sudo apt-get install -y libio-socket-ssl-perl
wget https://www.percona.com/downloads/percona-toolkit/2.2.13/deb/percona-toolkit_2.2.13_all.deb
sudo dpkg -i percona-toolkit_2.2.13_all.deb
