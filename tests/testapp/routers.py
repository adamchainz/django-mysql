class TestAppRouter(object):

    def allow_relation(self, obj1, obj2, **hints):
        if obj1._meta.app_label == 'testapp' or obj2._meta.app_label == 'testapp':
            return True
        return None

    def allow_migrate(self, db, app_label, **hints):
        if app_label == 'testapp':
            return db == 'default' or db == 'other'
        return None
