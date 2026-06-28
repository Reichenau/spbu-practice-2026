from __future__ import annotations

from ..model.query_ast import (
    BinaryExpression,
    ComparisonExpression,
    DistanceReturn,
    DslQuery,
    Expression,
    FieldRef,
    FunctionExpression,
    NotExpression,
    PairLimit,
    Pattern,
    Query,
    Selector,
    SpanSpec,
    WithinConstraint,
)
from .document_index import DocumentIndex


class QueryValidator:
    def validate(self, query: Query, index: DocumentIndex) -> None:
        known_entities = index.entities() | {"symbol"}
        missing_entities = sorted(self._collect_entities(query) - known_entities)
        if missing_entities:
            raise ValueError(
                "Query references unknown AST entities: "
                + ", ".join(missing_entities)
            )

        # Семантическая валидация по kind
        if query.kind == "CONTEXT":
            if query.patterns is None or len(query.patterns) == 0:
                raise ValueError("CONTEXT query must have at least one pattern")
            if query.limit is None or not isinstance(query.limit, int) or query.limit <= 0:
                raise ValueError("CONTEXT query must have a positive integer LIMIT")
        elif query.kind == "DISTANCE":
            if query.target is None:
                raise ValueError("DISTANCE query must have a target selector")
            if not isinstance(query.limit, PairLimit):
                raise ValueError("DISTANCE query must have a PairLimit")
            distance_returns = [item for item in query.returns or () if isinstance(item, DistanceReturn)]
            if len(distance_returns) != 1:
                raise ValueError("DISTANCE query requires exactly one RETURN distance(entity) item")
        elif query.kind == "FIND":
            pass
        else:
            raise ValueError(f"Unknown query kind: {query.kind}")

    def _collect_entities(self, query: Query) -> set[str]:
        items: set[str] = set()
        items.add(query.source.entity_name)
        if query.target is not None:
            items.add(query.target.entity_name)
        for pattern in query.patterns or ():
            source = pattern.source
            if isinstance(source, Selector):
                items.update(self._collect_selector_entities(source))
        for within in query.within:
            items.add(within.entity_name)
        if query.where is not None:
            items.update(self._collect_expression_entities(query.where))
        if query.returns:
            for item in query.returns:
                if isinstance(item, DistanceReturn):
                    items.add(item.entity_name)
        return items

    def _collect_selector_entities(self, selector: Selector) -> set[str]:
        items = {selector.entity_name}
        if selector.predicate is not None:
            items.update(self._collect_expression_entities(selector.predicate))
        return items

    def _collect_expression_entities(self, expression: Expression) -> set[str]:
        if isinstance(expression, ComparisonExpression):
            return set()
        if isinstance(expression, NotExpression):
            return self._collect_expression_entities(expression.operand)
        if isinstance(expression, BinaryExpression):
            return self._collect_expression_entities(expression.left) | self._collect_expression_entities(expression.right)
        if isinstance(expression, FunctionExpression):
            items: set[str] = set()
            for argument in expression.arguments:
                if isinstance(argument, Selector):
                    items.update(self._collect_selector_entities(argument))
                elif isinstance(argument, SpanSpec):
                    items.add(argument.entity_name)
                elif isinstance(argument, FieldRef):
                    continue
            return items
        return set()