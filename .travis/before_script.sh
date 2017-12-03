#!/bin/bash

set -e
set -x

# percona-toolkit - have to use non-apt version since Travis' ubuntu 12.04 repo
# is way out of date
sudo apt-get update -qq
sudo apt-get install -y libio-socket-ssl-perl
wget https://www.percona.com/downloads/percona-toolkit/2.2.13/deb/percona-toolkit_2.2.13_all.deb
sudo dpkg -i percona-toolkit_2.2.13_all.deb

# DB

# Nuke default
sudo rm -rf /var/lib/mysql

if [[ $DB == 'mysql' ]]
then
    # Install new
    sudo add-apt-repository "deb http://repo.mysql.com/apt/ubuntu/ trusty mysql-$DB_VERSION"
    sudo cat .travis/oracle.pgp-key | sudo apt-key add -
    sudo apt-get update
    echo 'Package: *
Pin: origin repo.mysql.com
Pin-Priority: 10000' | sudo tee /etc/apt/preferences.d/pin-mysql.pref
    sudo DEBIAN_FRONTEND=noninteractive apt-get install -y mysql-server
elif [[ $DB == 'mariadb' ]]
then
    # Install
    sudo apt-get install -y software-properties-common
    sudo apt-key adv --recv-keys --keyserver hkp://keyserver.ubuntu.com:80 0xcbcb082a1bb943db
    sudo add-apt-repository "deb [arch=amd64,i386,ppc64el] http://sfo1.mirrors.digitalocean.com/mariadb/repo/$DB_VERSION/ubuntu trusty main"
    echo 'Package: *
Pin: origin sfo1.mirrors.digitalocean.com
Pin-Priority: 10000' | sudo tee /etc/apt/preferences.d/pin-mariadb.pref
    sudo apt-get update
    PACKAGES="mariadb-server mariadb-client"
    if [[ $DB_VERSION != '10.2' ]]
    then
        PACKAGES="$PACKAGES libmariadbclient-dev"
    fi
    # shellcheck disable=SC2086
    sudo DEBIAN_FRONTEND=noninteractive apt-get install -y $PACKAGES
fi

sudo mysql -u root -e "set global binlog_format=MIXED"

sudo mysql -u root -e "create user travis@localhost identified by '';" || true

sudo mysql -u root -e 'grant all privileges on *.* to travis@localhost;'
