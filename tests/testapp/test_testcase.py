from django_mysql.test.cases import FasterTransactionTestCase

from tests.testapp.models import VanillaAuthor, NameAuthor


class TestFasterTransactionTestCase(FasterTransactionTestCase):

    def test_empty_1(self):
        assert VanillaAuthor.objects.count() == 0
        assert NameAuthor.objects.count() == 0
        VanillaAuthor.objects.create(name="Van")
        NameAuthor.objects.create(name="Name")

    def test_empty_2(self):
        assert VanillaAuthor.objects.count() == 0
        assert NameAuthor.objects.count() == 0
        VanillaAuthor.objects.create(name="Van 2")
        NameAuthor.objects.create(name="Name 2")
