Indexes
=======

.. currentmodule:: django_mysql.models

Django-MySQL includes a custom index class that extends Django's built-in index
functionality for MySQL-specific features.

ColumnPrefixIndex
-------------------

.. class:: ColumnPrefixIndex(*expressions, prefix_lengths, **kwargs)

    A custom index class that allows you to create indexes with column prefix
    lengths in MySQL. This is particularly useful for indexing ``TEXT`` or long
    ``VARCHAR`` columns where you want to index only the first N characters.

    MySQL allows you to create indexes that only include the first N characters of
    a column, which can be both space-efficient and useful for queries that match
    against the start of strings, such as ``istartswith`` lookups.

    For more details about column prefix indexes in MySQL, see the
    `MySQL documentation on CREATE INDEX column-prefixes
    <https://dev.mysql.com/doc/refman/8.0/en/create-index.html#create-index-column-prefixes>`_.

    **Arguments:**

    * ``expressions``: The fields or expressions to index
    * ``prefix_lengths``: A sequence of integers specifying the prefix length for each column
    * ``**kwargs``: Additional arguments passed to Django's Index class

    **Example:**

    .. code-block:: python

        from django.db import models
        from django_mysql.models import ColumnPrefixIndex


        class Article(models.Model):
            title = models.CharField(max_length=200)
            content = models.TextField()

            class Meta:
                indexes = [
                    ColumnPrefixIndex(
                        fields=["title", "content"],
                        prefix_lengths=(10, 50),
                        name="title_content_prefix_idx",
                    ),
                ]

    This will create an index equivalent to the following SQL:

    .. code-block:: sql

        CREATE INDEX title_content_prefix_idx ON article (title(10), content(50));

    Such indexes can be particularly efficient for ``istartswith`` queries:

    .. code-block:: python

        # This query can use the prefix index
        Article.objects.filter(title__istartswith="Django")
