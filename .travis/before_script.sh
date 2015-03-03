#!/bin/bash -e

# Add percona
sudo apt-get install -y percona-toolkit

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
  yes Y | sudo apt-get install -y mariadb-server
fi

mysql -e 'create database if not exists test;'
