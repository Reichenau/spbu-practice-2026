from __future__ import annotations

from dataclasses import dataclass
from typing import Union

from ..model.query_ast import DslQuery
from .token import DslToken


@dataclass(slots=True)
class ParseDslRequest:
    source: str


@dataclass(slots=True)
class TokenizeDslRequest:
    source: str


@dataclass(slots=True)
class DslTokenized:
    tokens: list[DslToken]


@dataclass(slots=True)
class ParseTokenStreamRequest:
    tokens: list[DslToken]


@dataclass(slots=True)
class ContinueQueryClassification:
    pass


@dataclass(slots=True)
class ContinueContextSpanParsing:
    pass


@dataclass(slots=True)
class ContinueContextPatternParsing:
    pass


@dataclass(slots=True)
class ContinueContextConstraintParsing:
    pass


@dataclass(slots=True)
class ContinueFindTargetParsing:
    pass


@dataclass(slots=True)
class ContinueFindConstraintParsing:
    pass


@dataclass(slots=True)
class DslQueryParsed:
    query: DslQuery


@dataclass(slots=True)
class DslParseFailed:
    error: Exception


CoordinatorMessage = Union[
    ParseDslRequest,
    DslTokenized,
    DslQueryParsed,
    DslParseFailed,
]

LexerMessage = Union[TokenizeDslRequest]

QueryParserMessage = Union[
    ParseTokenStreamRequest,
    ContinueQueryClassification,
    ContinueContextSpanParsing,
    ContinueContextPatternParsing,
    ContinueContextConstraintParsing,
    ContinueFindTargetParsing,
    ContinueFindConstraintParsing,
]

CollectorMessage = Union[DslQueryParsed, DslParseFailed]
