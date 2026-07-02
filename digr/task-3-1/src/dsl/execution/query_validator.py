from __future__ import annotations

from ..model.query_ast import (
    BinaryExpression,
    ComparisonExpression,
    ContextQuery,
    DistanceQuery,
    DistanceReturn,
    DslQuery,
    Expression,
    FieldRef,
    FindQuery,
    FunctionExpression,
    NotExpression,
    Pattern,
    Selector,
    SpanSpec,
    WithinConstraint,
)
from .document_index import DocumentIndex


class QueryValidator:
    def validate(self, query: DslQuery, index: DocumentIndex) -> None:
        known_entities = index.entities() | {"symbol"}
        missing_entities = sorted(self._collect_entities(query) - known_entities)
        if missing_entities:
            raise ValueError(
                "Query references unknown AST entities: "
                + ", ".join(missing_entities)
            )

    def _collect_entities(self, query: DslQuery) -> set[str]:
        items: set[str] = set()
        if isinstance(query, ContextQuery):
            items.add(query.span.entity_name)
            for pattern in query.patterns:
                items.update(self._collect_pattern_entities(pattern))
            for within in query.within:
                items.add(within.entity_name)
            for item in query.returns or ():
                if isinstance(item, DistanceReturn):
                    items.add(item.entity_name)
            if query.where is not None:
                items.update(self._collect_expression_entities(query.where))
            return items

        if isinstance(query, DistanceQuery):
            items.update(self._collect_selector_entities(query.left))
            items.update(self._collect_selector_entities(query.right))
            for within in query.within:
                items.add(within.entity_name)
            distance_returns = [item for item in query.returns or () if isinstance(item, DistanceReturn)]
            if len(distance_returns) != 1:
                raise ValueError("DISTANCE query requires exactly one RETURN distance(entity) item")
            for item in distance_returns:
                items.add(item.entity_name)
            return items

        items.add(query.entity_name)
        for within in query.within or ():
            items.add(within.entity_name)
        if query.where is not None:
            items.update(self._collect_expression_entities(query.where))
        return items

    def _collect_pattern_entities(self, pattern: Pattern) -> set[str]:
        source = pattern.source
        if isinstance(source, Selector):
            return self._collect_selector_entities(source)
        return set()

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
