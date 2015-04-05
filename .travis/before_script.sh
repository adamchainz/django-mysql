#!/bin/bash -e

# Add percona - have to use non-apt version since Travis' ubuntu 12.04 repo is
# way out of date
sudo apt-get install -y libio-socket-ssl-perl
wget http://www.percona.com/downloads/percona-toolkit/2.2.13/deb/percona-toolkit_2.2.13_all.deb
sudo dpkg -i percona-toolkit_2.2.13_all.deb


# Add database

if [[ $DB == 'mysql' ]]
then
  if [[ $DB_VERSION == '5.5' ]]
  then
    sudo service mysql start || true  # Travis default installed version
  else
    sudo apt-get -y remove mysql-server
    sudo apt-get -y autoremove
    sudo apt-get -y install software-properties-common
    sudo add-apt-repository -y ppa:ondrej/mysql-5.6
    sudo apt-get update
    yes Y | sudo apt-get -y install mysql-server
  fi

elif [[ $DB == 'mariadb' ]]
then
  sudo service mysql stop
  sudo apt-get install -y python-software-properties
  sudo apt-key adv --recv-keys --keyserver hkp://keyserver.ubuntu.com:80 0xcbcb082a1bb943db
  sudo add-apt-repository "deb http://ftp.osuosl.org/pub/mariadb/repo/$DB_VERSION/ubuntu precise main"
  sudo apt-get update -qq
  yes Y | sudo apt-get install -y mariadb-server libmariadbclient-dev
fi

mysql -e 'create database if not exists test;'
