from __future__ import annotations

from ..model.query_ast import (
    BinaryExpression,
    ComparisonExpression,
    ContextQuery,
    CountConstraint,
    DistanceQuery,
    DistanceReturn,
    DslQuery,
    DslValue,
    Expression,
    FieldRef,
    FindQuery,
    FunctionExpression,
    NotExpression,
    PairLimit,
    Pattern,
    RegexLiteral,
    ReturnItem,
    Selector,
    SpanSpec,
    WithinConstraint,
)
from .errors import DslSyntaxError
from .token import DslToken
from .token_kind import TokenKind

_COUNT_OPERATOR_KINDS = {
    TokenKind.EQ: "=",
    TokenKind.LT: "<",
    TokenKind.LTE: "<=",
    TokenKind.GT: ">",
    TokenKind.GTE: ">=",
}

_COMPARISON_OPERATOR_KINDS = {
    **_COUNT_OPERATOR_KINDS,
    TokenKind.NE: "!=",
    TokenKind.MATCH: "~=",
    TokenKind.NOT_MATCH: "!~=",
}


class DslTokenStreamParser:
    def __init__(self, tokens: list[DslToken]) -> None:
        self._tokens = tokens
        self._index = 0

    @property
    def current(self) -> DslToken:
        return self._tokens[self._index]

    def peek(self, offset: int = 1) -> DslToken:
        position = self._index + offset
        if position >= len(self._tokens):
            return self._tokens[-1]
        return self._tokens[position]

    def advance(self) -> DslToken:
        token = self.current
        if token.kind is not TokenKind.EOF:
            self._index += 1
        return token

    def match(self, *kinds: TokenKind) -> DslToken | None:
        if self.current.kind in kinds:
            return self.advance()
        return None

    def expect(self, kind: TokenKind, message: str) -> DslToken:
        if self.current.kind is not kind:
            raise self._error(message)
        return self.advance()

    def parse_query(self) -> DslQuery:
        if self.current.kind is TokenKind.CONTEXT:
            query = self.parse_context_query()
        elif self.current.kind is TokenKind.FIND:
            query = self.parse_find_query()
        elif self.current.kind is TokenKind.DISTANCE:
            query = self.parse_distance_query()
        else:
            raise self._error("Query must start with CONTEXT, FIND, or DISTANCE")
        self.consume_query_terminator()
        self.expect(TokenKind.EOF, "Unexpected tokens after end of query")
        return query

    def parse_context_prefix(self) -> SpanSpec:
        self.expect(TokenKind.CONTEXT, "Expected CONTEXT")
        span = self.parse_span_spec()
        self.expect(TokenKind.FOR, "Expected FOR after context span")
        return span

    def parse_find_prefix(self) -> str:
        self.expect(TokenKind.FIND, "Expected FIND")
        return self.parse_identifier("Expected entity name after FIND")

    def parse_context_query(self) -> ContextQuery:
        span = self.parse_context_prefix()
        patterns = self.parse_pattern_list()
        within = self.parse_within_clauses()
        where = self.parse_where_clause()
        returns = self.parse_return_clause()
        return ContextQuery(span=span, patterns=patterns, within=within, where=where, returns=returns)

    def parse_find_query(self) -> FindQuery:
        entity_name = self.parse_find_prefix()
        where = self.parse_where_clause()
        within = self.parse_within_clauses()
        returns = self.parse_return_clause()
        return FindQuery(entity_name=entity_name, where=where, within=within, returns=returns)

    def parse_distance_query(self) -> DistanceQuery:
        self.expect(TokenKind.DISTANCE, "Expected DISTANCE")
        left = self.parse_selector()
        self.expect(TokenKind.TO, "Expected TO after left distance selector")
        right = self.parse_selector()
        within = self.parse_within_clauses()
        limit_pairs = self.parse_limit_pairs_clause()
        returns = self.parse_return_clause()
        return DistanceQuery(
            left=left,
            right=right,
            within=within,
            limit_pairs=limit_pairs,
            returns=returns,
        )

    def parse_context_constraints(self) -> tuple[list[WithinConstraint], Expression | None, list[ReturnItem]]:
        within = self.parse_within_clauses()
        where = self.parse_where_clause()
        returns = self.parse_return_clause()
        self.consume_query_terminator()
        self.expect(TokenKind.EOF, "Unexpected tokens after end of CONTEXT query")
        return within, where, returns

    def parse_find_constraints(self) -> tuple[Expression | None, list[WithinConstraint], list[ReturnItem]]:
        where = self.parse_where_clause()
        within = self.parse_within_clauses()
        returns = self.parse_return_clause()
        self.consume_query_terminator()
        self.expect(TokenKind.EOF, "Unexpected tokens after end of FIND query")
        return where, within, returns

    def consume_query_terminator(self) -> None:
        self.match(TokenKind.SEMICOLON)

    def parse_within_clauses(self) -> list[WithinConstraint]:
        items: list[WithinConstraint] = []
        while self.match(TokenKind.WITHIN):
            entity_name = self.parse_identifier("Expected entity name after WITHIN")
            self.expect(TokenKind.LBRACKET, "Expected '[' after WITHIN entity name")
            constraint = self.parse_count_constraint()
            self.expect(TokenKind.RBRACKET, "Expected ']' after WITHIN constraint")
            items.append(WithinConstraint(entity_name=entity_name, constraint=constraint))
        return items

    def parse_where_clause(self):
        if not self.match(TokenKind.WHERE):
            return None
        return self.parse_boolean_expression()

    def parse_limit_pairs_clause(self) -> PairLimit:
        if not self.match(TokenKind.LIMIT_PAIRS):
            return PairLimit(mode="nearest")
        if self.current.kind is TokenKind.INTEGER:
            value = self.advance().value
            if value <= 0:
                raise self._error("LIMIT_PAIRS integer must be positive")
            return PairLimit(mode="k", value=value)
        mode = self.parse_identifier("Expected LIMIT_PAIRS mode")
        if mode not in {"nearest", "all_nearest", "all"}:
            raise self._error("Expected LIMIT_PAIRS nearest, all_nearest, all, or positive integer")
        return PairLimit(mode=mode)

    def parse_return_clause(self) -> list[ReturnItem]:
        if not self.match(TokenKind.RETURN):
            return []
        items = [self.parse_return_item()]
        while self.match(TokenKind.COMMA):
            items.append(self.parse_return_item())
        return items

    def parse_return_item(self) -> ReturnItem:
        if self.current.kind is TokenKind.DISTANCE:
            name = self.advance().value
        else:
            name = self.parse_identifier("Expected return item")
        if name == "distance" and self.match(TokenKind.LPAREN):
            entity_name = self.parse_identifier("Expected entity name in distance()")
            self.expect(TokenKind.RPAREN, "Expected ')' after distance entity")
            return DistanceReturn(entity_name=entity_name)
        return name

    def parse_pattern_list(self) -> list[Pattern]:
        items = [self.parse_pattern()]
        while self.match(TokenKind.COMMA):
            items.append(self.parse_pattern())
        return items

    def parse_pattern(self) -> Pattern:
        alias: str | None = None
        if self.current.kind is TokenKind.IDENTIFIER and self.peek().kind is TokenKind.COLON:
            alias = self.advance().value
            self.advance()

        if self.current.kind is TokenKind.STRING:
            token = self.advance()
            return Pattern(source=token.value, alias=alias)
        if self.current.kind is TokenKind.REGEX:
            return Pattern(source=self.parse_regex_literal(), alias=alias)
        return Pattern(source=self.parse_selector(), alias=alias)

    def parse_span_spec(self) -> SpanSpec:
        entity_name = self.parse_identifier("Expected entity name")
        self.expect(TokenKind.LBRACKET, "Expected '[' after entity name")
        constraint = self.parse_count_constraint()
        self.expect(TokenKind.RBRACKET, "Expected ']' after span constraint")
        return SpanSpec(entity_name=entity_name, constraint=constraint)

    def parse_count_constraint(self) -> CountConstraint:
        token = self.current
        operator = _COUNT_OPERATOR_KINDS.get(token.kind)
        if operator is None:
            raise self._error("Expected count operator")
        self.advance()
        integer_token = self.expect(TokenKind.INTEGER, "Expected integer after count operator")
        return CountConstraint(operator=operator, value=integer_token.value)

    def parse_boolean_expression(self):
        return self.parse_disjunction()

    def parse_disjunction(self):
        expression = self.parse_conjunction()
        while self.match(TokenKind.OR):
            right = self.parse_conjunction()
            expression = BinaryExpression(operator="OR", left=expression, right=right)
        return expression

    def parse_conjunction(self):
        expression = self.parse_negation()
        while self.match(TokenKind.AND):
            right = self.parse_negation()
            expression = BinaryExpression(operator="AND", left=expression, right=right)
        return expression

    def parse_negation(self):
        if self.match(TokenKind.NOT):
            return NotExpression(operand=self.parse_negation())
        return self.parse_predicate()

    def parse_predicate(self):
        if self.match(TokenKind.LPAREN):
            expression = self.parse_boolean_expression()
            self.expect(TokenKind.RPAREN, "Expected ')' after grouped expression")
            return expression
        if self.current.kind is TokenKind.IDENTIFIER and self.peek().kind is TokenKind.LPAREN:
            return self.parse_function_call()
        return self.parse_comparison()

    def parse_comparison(self) -> ComparisonExpression:
        left = self.parse_field_ref()
        operator_token = self.current
        operator = _COMPARISON_OPERATOR_KINDS.get(operator_token.kind)
        if operator is None:
            raise self._error("Expected comparison operator")
        self.advance()
        right = self.parse_value()
        return ComparisonExpression(left=left, operator=operator, right=right)

    def parse_function_call(self) -> FunctionExpression:
        name = self.parse_identifier("Expected function name")
        self.expect(TokenKind.LPAREN, "Expected '(' after function name")
        arguments = []
        if self.current.kind is not TokenKind.RPAREN:
            arguments.append(self.parse_argument())
            while self.match(TokenKind.COMMA):
                arguments.append(self.parse_argument())
        self.expect(TokenKind.RPAREN, "Expected ')' after function arguments")
        return FunctionExpression(name=name, arguments=arguments)

    def parse_argument(self):
        if self.current.kind in {TokenKind.STRING, TokenKind.REGEX, TokenKind.INTEGER, TokenKind.TRUE, TokenKind.FALSE, TokenKind.NULL}:
            return self.parse_value()
        if self.current.kind is not TokenKind.IDENTIFIER:
            raise self._error("Expected function argument")

        if self.peek().kind is TokenKind.LBRACKET:
            if self._looks_like_span_spec():
                return self.parse_span_spec()
            return self.parse_selector()
        if self.peek().kind is TokenKind.DOT:
            return self.parse_field_ref()
        return Selector(entity_name=self.parse_identifier("Expected selector name"))

    def parse_selector(self) -> Selector:
        entity_name = self.parse_identifier("Expected selector entity name")
        predicate = None
        if self.match(TokenKind.LBRACKET):
            if self._looks_like_count_constraint():
                raise self._error("Selector predicate cannot start with a count constraint")
            predicate = self.parse_boolean_expression()
            self.expect(TokenKind.RBRACKET, "Expected ']' after selector predicate")
        return Selector(entity_name=entity_name, predicate=predicate)

    def parse_field_ref(self) -> FieldRef:
        parts = [self.parse_identifier("Expected field name")]
        while self.match(TokenKind.DOT):
            parts.append(self.parse_identifier("Expected field name after '.'"))
        return FieldRef(parts=parts)

    def parse_value(self) -> DslValue:
        token = self.current
        if token.kind is TokenKind.STRING:
            self.advance()
            return token.value
        if token.kind is TokenKind.REGEX:
            return self.parse_regex_literal()
        if token.kind is TokenKind.INTEGER:
            self.advance()
            return token.value
        if token.kind is TokenKind.TRUE:
            self.advance()
            return True
        if token.kind is TokenKind.FALSE:
            self.advance()
            return False
        if token.kind is TokenKind.NULL:
            self.advance()
            return None
        raise self._error("Expected literal value")

    def parse_regex_literal(self) -> RegexLiteral:
        token = self.expect(TokenKind.REGEX, "Expected regex literal")
        return RegexLiteral(pattern=token.value["pattern"], flags=token.value["flags"])

    def parse_identifier(self, message: str) -> str:
        token = self.expect(TokenKind.IDENTIFIER, message)
        return token.value

    def _looks_like_span_spec(self) -> bool:
        return self.peek().kind is TokenKind.LBRACKET and self.peek(2).kind in _COUNT_OPERATOR_KINDS

    def _looks_like_count_constraint(self) -> bool:
        return self.current.kind in _COUNT_OPERATOR_KINDS

    def _error(self, message: str) -> DslSyntaxError:
        token = self.current
        return DslSyntaxError(message, offset=token.offset, line=token.line, column=token.column)
