from __future__ import annotations

from enum import Enum, auto


class DslCoordinatorState(Enum):
    IDLE = auto()
    WAITING_FOR_TOKENS = auto()
    WAITING_FOR_QUERY_AST = auto()
    COMPLETED = auto()


class DslQueryParserState(Enum):
    READY = auto()
    CLASSIFYING_QUERY = auto()
    PARSING_CONTEXT_SPAN = auto()
    PARSING_CONTEXT_PATTERNS = auto()
    PARSING_CONTEXT_CONSTRAINTS = auto()
    PARSING_FIND_TARGET = auto()
    PARSING_FIND_CONSTRAINTS = auto()


class DslWorkerState(Enum):
    READY = auto()


class DslCollectorState(Enum):
    EMPTY = auto()
    HAS_RESULT = auto()
    HAS_ERROR = auto()
