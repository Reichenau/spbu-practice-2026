from __future__ import annotations

from actor import Actor, ActorHandle

from ...model.query_ast import ContextQuery, FindQuery, Pattern, SpanSpec
from ...parsing.messages import (
    ContinueContextConstraintParsing,
    ContinueContextPatternParsing,
    ContinueContextSpanParsing,
    ContinueFindConstraintParsing,
    ContinueFindTargetParsing,
    ContinueQueryClassification,
    DslParseFailed,
    DslQueryParsed,
    ParseTokenStreamRequest,
    QueryParserMessage,
)
from ...parsing.recursive_descent_parser import DslTokenStreamParser
from ...parsing.states import DslQueryParserState
from ...parsing.token_kind import TokenKind


class DslQueryParserActor(Actor[DslQueryParserState, QueryParserMessage, QueryParserMessage]):
    def __init__(self, reply_to: ActorHandle[object] | None = None) -> None:
        super().__init__(DslQueryParserState, DslQueryParserState.READY)
        self._reply_to = reply_to
        self._parser: DslTokenStreamParser | None = None
        self._context_span: SpanSpec | None = None
        self._context_patterns: list[Pattern] = []
        self._find_entity_name: str | None = None

    def set_reply_to(self, handle: ActorHandle[object]) -> None:
        self._reply_to = handle

    def on_ready_parse_token_stream_request(self, message: ParseTokenStreamRequest) -> DslQueryParserState:
        self._parser = DslTokenStreamParser(message.tokens)
        self._context_span = None
        self._context_patterns = []
        self._find_entity_name = None
        self.put(ContinueQueryClassification())
        return DslQueryParserState.CLASSIFYING_QUERY

    def on_classifying_query_continue_query_classification(
            self, message: ContinueQueryClassification,
    ) -> DslQueryParserState:
        parser = self._require_parser()
        try:
            if parser.current.kind is TokenKind.CONTEXT:
                self.put(ContinueContextSpanParsing())
                return DslQueryParserState.PARSING_CONTEXT_SPAN
            if parser.current.kind is TokenKind.FIND:
                self.put(ContinueFindTargetParsing())
                return DslQueryParserState.PARSING_FIND_TARGET
            if parser.current.kind is TokenKind.DISTANCE:
                self._reply(DslQueryParsed(query=parser.parse_query()))
                return DslQueryParserState.READY
            raise parser._error("Query must start with CONTEXT, FIND, or DISTANCE")
        except Exception as error:
            return self._fail(error)

    def on_parsing_context_span_continue_context_span_parsing(
            self, message: ContinueContextSpanParsing,
    ) -> DslQueryParserState:
        parser = self._require_parser()
        try:
            self._context_span = parser.parse_context_prefix()
            self.put(ContinueContextPatternParsing())
            return DslQueryParserState.PARSING_CONTEXT_PATTERNS
        except Exception as error:
            return self._fail(error)

    def on_parsing_context_patterns_continue_context_pattern_parsing(
            self, message: ContinueContextPatternParsing,
    ) -> DslQueryParserState:
        parser = self._require_parser()
        try:
            self._context_patterns = parser.parse_pattern_list()
            self.put(ContinueContextConstraintParsing())
            return DslQueryParserState.PARSING_CONTEXT_CONSTRAINTS
        except Exception as error:
            return self._fail(error)

    def on_parsing_context_constraints_continue_context_constraint_parsing(
            self, message: ContinueContextConstraintParsing,
    ) -> DslQueryParserState:
        parser = self._require_parser()
        try:
            span = self._context_span
            if span is None:
                raise RuntimeError("context span was not parsed")
            within, where, returns = parser.parse_context_constraints()
            query = ContextQuery(
                span=span,
                patterns=list(self._context_patterns),
                within=within,
                where=where,
                returns=returns,
            )
            self._reply(DslQueryParsed(query=query))
            return DslQueryParserState.READY
        except Exception as error:
            return self._fail(error)

    def on_parsing_find_target_continue_find_target_parsing(
            self, message: ContinueFindTargetParsing,
    ) -> DslQueryParserState:
        parser = self._require_parser()
        try:
            self._find_entity_name = parser.parse_find_prefix()
            self.put(ContinueFindConstraintParsing())
            return DslQueryParserState.PARSING_FIND_CONSTRAINTS
        except Exception as error:
            return self._fail(error)

    def on_parsing_find_constraints_continue_find_constraint_parsing(
            self, message: ContinueFindConstraintParsing,
    ) -> DslQueryParserState:
        parser = self._require_parser()
        try:
            entity_name = self._find_entity_name
            if entity_name is None:
                raise RuntimeError("find target entity was not parsed")
            where, within, returns = parser.parse_find_constraints()
            self._reply(DslQueryParsed(query=FindQuery(
                entity_name=entity_name,
                where=where,
                within=within,
                returns=returns,
            )))
            return DslQueryParserState.READY
        except Exception as error:
            return self._fail(error)

    def _require_parser(self) -> DslTokenStreamParser:
        if self._parser is None:
            raise RuntimeError("parser is not initialized")
        return self._parser

    def _reply(self, message: object) -> None:
        if self._reply_to is None:
            raise RuntimeError("reply_to handle is not configured")
        self._reply_to.tell(message)

    def _fail(self, error: Exception) -> DslQueryParserState:
        self._reply(DslParseFailed(error))
        return DslQueryParserState.READY
