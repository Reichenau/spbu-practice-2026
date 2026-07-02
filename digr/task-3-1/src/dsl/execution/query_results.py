from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from document_ast.model.ast_node import AstNode

from ..model.query_ast import ContextQuery, DistanceQuery, DistanceReturn, FindQuery, ReturnItem


def _render_span(start: int, end: int) -> dict[str, int]:
    return {"start": start, "end": end}


def render_compact_node(node: AstNode) -> dict[str, Any]:
    return {
        "entity": node.entity,
        "text": node.text,
        "start": node.start,
        "end": node.end,
        "metadata": node.metadata,
    }


def _return_name(item: ReturnItem) -> str:
    if isinstance(item, DistanceReturn):
        return "distance"
    return item


def _render_return_item(item: ReturnItem) -> str:
    if isinstance(item, DistanceReturn):
        return f"distance({item.entity_name})"
    return item


def _return_items(items: list[ReturnItem] | None, default: list[ReturnItem]) -> list[ReturnItem]:
    return list(items or default)


@dataclass(slots=True)
class PatternMatchResult:
    name: str
    source_type: str
    matched_text: str | None = None
    nodes: list[AstNode] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        result = {
            "name": self.name,
            "source_type": self.source_type,
        }
        if self.matched_text is not None:
            result["matched_text"] = self.matched_text
        if self.nodes:
            result["nodes"] = [render_compact_node(node) for node in self.nodes]
        return result


@dataclass(slots=True)
class FindMatch:
    node: AstNode

    def render(self, return_items: list[ReturnItem], source_path: str) -> dict[str, Any]:
        return_names = {_return_name(item) for item in return_items}
        result: dict[str, Any] = {}
        if "nodes" in return_names:
            result["nodes"] = self.node.to_dict()
        if "text" in return_names:
            result["text"] = self.node.text
        if "span" in return_names:
            result["span"] = _render_span(self.node.start, self.node.end)
        if "source" in return_names:
            result["source"] = source_path
        return result


@dataclass(slots=True)
class ContextWindowMatch:
    base_entity: str
    nodes: list[AstNode]
    text: str
    start: int
    end: int
    matches: list[PatternMatchResult]
    distances: list[dict[str, Any]] = field(default_factory=list)

    def render(self, return_items: list[ReturnItem], source_path: str) -> dict[str, Any]:
        return_names = {_return_name(item) for item in return_items}
        result: dict[str, Any] = {}
        if "window" in return_names:
            result["window"] = {
                "base_entity": self.base_entity,
                "span": _render_span(self.start, self.end),
                "text": self.text,
                "nodes": [render_compact_node(node) for node in self.nodes],
            }
        if "text" in return_names:
            result["text"] = self.text
        if "span" in return_names:
            result["span"] = _render_span(self.start, self.end)
        if "matches" in return_names:
            result["matches"] = [match.to_dict() for match in self.matches]
        if "distance" in return_names:
            result["distances"] = self.distances
        if "source" in return_names:
            result["source"] = source_path
        return result


@dataclass(slots=True)
class DistancePairMatch:
    left: AstNode
    right: AstNode
    distance: int
    unit: str

    def render(self) -> dict[str, Any]:
        return {
            "left": render_compact_node(self.left),
            "right": render_compact_node(self.right),
            "span": _render_span(min(self.left.start, self.right.start), max(self.left.end, self.right.end)),
            "distance": {
                "unit": self.unit,
                "value": self.distance,
            },
        }


@dataclass(slots=True)
class FindQueryExecutionResult:
    query: FindQuery
    source_path: str
    matches: list[FindMatch]

    def to_dict(self) -> dict[str, Any]:
        query_returns = _return_items(self.query.returns, ["nodes", "count"])
        return_items = [item for item in query_returns if _return_name(item) != "count"]
        return {
            "type": "find_query_execution_result",
            "count": len(self.matches),
            "returns": [_render_return_item(item) for item in query_returns],
            "items": [match.render(return_items, self.source_path) for match in self.matches] if return_items else [],
        }


@dataclass(slots=True)
class ContextQueryExecutionResult:
    query: ContextQuery
    source_path: str
    windows: list[ContextWindowMatch]

    def to_dict(self) -> dict[str, Any]:
        query_returns = _return_items(self.query.returns, ["window", "count"])
        return_items = [item for item in query_returns if _return_name(item) != "count"]
        return {
            "type": "context_query_execution_result",
            "count": len(self.windows),
            "returns": [_render_return_item(item) for item in query_returns],
            "items": [window.render(return_items, self.source_path) for window in self.windows] if return_items else [],
        }


@dataclass(slots=True)
class DistanceQueryExecutionResult:
    query: DistanceQuery
    source_path: str
    pairs: list[DistancePairMatch]

    def to_dict(self) -> dict[str, Any]:
        query_returns = _return_items(self.query.returns, ["pairs", "stats", "count"])
        return_names = {_return_name(item) for item in query_returns}
        payload: dict[str, Any] = {
            "type": "distance_query_execution_result",
            "count": len(self.pairs),
            "returns": [_render_return_item(item) for item in query_returns],
        }
        if "pairs" in return_names:
            payload["items"] = [pair.render() for pair in self.pairs]
        else:
            payload["items"] = []
        if "stats" in return_names:
            payload["stats"] = self._stats()
        if "source" in return_names:
            payload["source"] = self.source_path
        return payload

    def _stats(self) -> dict[str, Any]:
        values = [pair.distance for pair in self.pairs]
        if not values:
            return {"count": 0, "mean": None, "variance": None, "min": None, "max": None}
        mean = sum(values) / len(values)
        variance = sum((value - mean) ** 2 for value in values) / len(values)
        return {
            "count": len(values),
            "mean": mean,
            "variance": variance,
            "min": min(values),
            "max": max(values),
        }


DslExecutionResult = FindQueryExecutionResult | ContextQueryExecutionResult | DistanceQueryExecutionResult
