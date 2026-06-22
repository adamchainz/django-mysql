from __future__ import annotations

import os
import subprocess
import time
import warnings

import MySQLdb
import pytest
from django.conf import settings


@pytest.fixture(scope="session", autouse=True)
def mysql_server():
    image = os.environ.get("DB_IMAGE", "mariadb:11.4")
    name = f"django-mysql-test-{os.getpid()}"

    subprocess.run(
        [
            "docker",
            "run",
            "--detach",
            "--name",
            name,
            "-e",
            "MYSQL_ROOT_PASSWORD=hunter2",
            "--publish",
            "127.0.0.1::3306",
            image,
        ],
        check=True,
    )

    try:
        port = (
            subprocess.check_output(
                [
                    "docker",
                    "inspect",
                    name,
                    "--format",
                    '{{(index (index .NetworkSettings.Ports "3306/tcp") 0).HostPort}}',
                ]
            )
            .decode()
            .strip()
        )

        for db in settings.DATABASES.values():
            if db["ENGINE"] != "django.db.backends.sqlite3":
                db["HOST"] = "127.0.0.1"
                db["PORT"] = port
                db["USER"] = "root"
                db["PASSWORD"] = "hunter2"

        deadline = time.monotonic() + 60
        while True:
            try:
                conn = MySQLdb.connect(
                    host="127.0.0.1",
                    port=int(port),
                    user="root",
                    password="hunter2",
                )
                conn.close()
                break
            except MySQLdb.OperationalError:
                if time.monotonic() > deadline:
                    raise RuntimeError("MySQL did not become ready in time")
                time.sleep(0.5)

        yield
    finally:
        subprocess.run(["docker", "rm", "--force", name], check=True)


# MySQL 5.7 warns about some sql mode changes
warnings.filterwarnings("ignore", r".*Changing sql mode.*")
warnings.filterwarnings("ignore", r".*sql modes should be used with strict mode.*")
# MySQL 5.7 turned 'explain' into 'explain extended' so it always warns the
# optimized query
warnings.filterwarnings("ignore", r".*/\* select#\d+ \*/")
# MySQL 5.7 deprecated some query hints
warnings.filterwarnings("ignore", r".*'SQL_CACHE' is deprecated.*")
warnings.filterwarnings("ignore", r".*'SQL_NO_CACHE' is deprecated.*")
