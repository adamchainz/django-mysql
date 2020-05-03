from django.db.backends.mysql.base import DatabaseWrapper as BaseDatabaseWrapper


class DatabaseWrapper(BaseDatabaseWrapper):
    def init_connection_state(self):
        if not self.mysql_is_mariadb and self.mysql_version >= (8,):
            sql_mode = ",".join(
                [
                    "ERROR_FOR_DIVISION_BY_ZERO",
                    "NO_ZERO_DATE",
                    "NO_ZERO_IN_DATE",
                    "STRICT_TRANS_TABLES",
                ]
            )
        else:
            sql_mode = ",".join(
                [
                    "ERROR_FOR_DIVISION_BY_ZERO",
                    "NO_AUTO_CREATE_USER",
                    "NO_ZERO_DATE",
                    "NO_ZERO_IN_DATE",
                    "STRICT_TRANS_TABLES",
                ]
            )
        with self.cursor() as cursor:
            cursor.execute(
                """
                SET sql_mode=%s, innodb_strict_mode=1;
                """,
                (sql_mode,),
            )
            cursor.execute("SET NAMES 'utf8mb4' COLLATE 'utf8mb4_general_ci';")
        super().init_connection_state()
