from __future__ import annotations


class NothingOnSQLiteRouter:
    def allow_migrate(self, db, app_label, **hints):
        return db in ("default", "other")
