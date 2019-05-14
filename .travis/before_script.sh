#!/bin/bash

set -e
set -x

# DB

if [[ $DB == 'mysql' ]]
then
    DOCKER_IMAGE="mysql:$DB_VERSION"
elif [[ $DB == 'mariadb' ]]
then
    DOCKER_IMAGE="mariadb:$DB_VERSION"
else
    echo "unknown DB $DB"
    exit 1
fi

docker pull "$DOCKER_IMAGE"
docker run --name mysql --env MYSQL_ALLOW_EMPTY_PASSWORD=true --env 'MYSQL_ROOT_HOST=%' -p 3306:3306 -d "$DOCKER_IMAGE"
set +x
until mysql -u root --protocol=TCP -e 'select 1'; do
    sleep 1
done
set -x
mysql -u root --protocol=TCP -e "
SET GLOBAL binlog_format=MIXED;
CREATE USER travis@'%' IDENTIFIED BY '';
GRANT ALL PRIVILEGES ON *.* TO travis@'%';"

# Install Percona default
sudo apt-get update -qq
sudo apt-get install -y percona-toolkit
