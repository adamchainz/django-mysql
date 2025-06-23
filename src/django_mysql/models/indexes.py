from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from django.db.backends.base.schema import BaseDatabaseSchemaEditor
from django.db.backends.ddl_references import Statement
from django.db.models import Index, Model
from django.db.models.expressions import BaseExpression, Combinable


class ColumnPrefixIndex(Index):
    def __init__(
        self,
        *expressions: BaseExpression | Combinable | str,
        prefix_lengths: Sequence[int],
        **kwargs: Any,
    ) -> None:
        super().__init__(*expressions, **kwargs)
        self.prefix_lengths = tuple(prefix_lengths)

    def deconstruct(self) -> Any:
        path, args, kwargs = super().deconstruct()
        if self.prefix_lengths is not None:
            kwargs["prefix_lengths"] = self.prefix_lengths
        return path, args, kwargs

    def create_sql(
        self,
        model: type[Model],
        schema_editor: BaseDatabaseSchemaEditor,
        using: str = "",
        **kwargs: Any,
    ) -> Statement:
        statement = super().create_sql(model, schema_editor, using=using, **kwargs)
        qn = schema_editor.quote_name
        statement.parts["columns"] = ", ".join(
            f"{qn(model._meta.get_field(field).column)}({length})"
            for field, length in zip(self.fields, self.prefix_lengths)
        )
        return statement
