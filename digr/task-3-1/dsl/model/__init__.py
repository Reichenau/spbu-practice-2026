from .query_ast import (
    BinaryExpression,
    ComparisonExpression,
    CountConstraint,
    DslValue,
    Expression,
    FieldRef,
    FunctionExpression,
    NotExpression,
    PairLimit,
    Pattern,
    Query,
    RegexLiteral,
    ReturnItem,
    Selector,
    SpanSpec,
    WithinConstraint,
)

# Алиасы для обратной совместимости со старым кодом
FindQuery = Query
ContextQuery = Query
DistanceQuery = Query
DslQuery = Query

__all__ = [
    "BinaryExpression",
    "ComparisonExpression",
    "ContextQuery",
    "CountConstraint",
    "DistanceQuery",
    "DslQuery",
    "DslValue",
    "Expression",
    "FieldRef",
    "FindQuery",
    "FunctionExpression",
    "NotExpression",
    "PairLimit",
    "Pattern",
    "Query",
    "RegexLiteral",
    "ReturnItem",
    "Selector",
    "SpanSpec",
    "WithinConstraint",
]