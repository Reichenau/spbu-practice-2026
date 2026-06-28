import re
from typing import List, Dict, Optional
from dsl import ActorDslEngine
from document_ast import AstDocument


class PatternBasedRelationExtractor:
    def __init__(self, templates: Dict[str, List[str]]):
        """
        templates: словарь, где ключ – тип отношения, значение – список шаблонных фраз.
        Пример: {'part_of': ['является частью', 'есть часть', 'входит в состав']}
        """
        self.templates = templates
        self.engine = ActorDslEngine()

    def extract(self, document: AstDocument, terms: List[str]) -> List[Dict]:
        """
        Для каждой пары терминов и каждого типа отношений выполняет DSL-запрос,
        ища шаблон в пределах одного предложения (можно изменить на абзац или другое окно).
        Возвращает список найденных отношений в виде dict.
        """
        results = []
        for i, t1 in enumerate(terms):
            for t2 in terms[i+1:]:
                for rel_type, patterns in self.templates.items():
                    # Строим regex из шаблонов, экранируем спецсимволы
                    pattern = "|".join(re.escape(p) for p in patterns)
                    query = f"""
                    CONTEXT sentence LIMIT 1
                    FOR "{t1}", "{t2}", /{pattern}/
                    RETURN window, matches
                    """
                    res = self.engine.execute(document, query)
                    if res.count > 0:
                        window_data = res.to_dict()["items"][0]["window"]
                        results.append({
                            "relation_type": rel_type,
                            "term1": t1,
                            "term2": t2,
                            "context": window_data["text"],
                            "span": window_data["span"],
                        })
        return results

    def extract_using_ast_entities(self, document: AstDocument, entity_name: str = "definition") -> List[Dict]:
        """
        Альтернативный метод: вместо списка терминов (строк) извлекает все сущности
        указанного типа (например, definition) и ищет отношения между ними,
        используя их метаданные (например, metadata.name) как имена терминов.
        """
        # Получить все узлы выбранной сущности
        from dsl import ActorDslParser
        parser = ActorDslParser()
        query = parser.parse(f"FIND {entity_name} RETURN nodes")
        result = self.engine.execute(document, query)
        items = result.to_dict().get("items", [])
        terms = []
        for item in items:
            node = item.get("nodes")
            if node:
                # Используем metadata.name как термин, если есть, иначе текст
                name = node.get("metadata", {}).get("name") or node.get("text", "").strip()
                if name:
                    terms.append(name)
        # Удаляем дубликаты и пустые строки
        terms = list(set([t for t in terms if t]))
        return self.extract(document, terms)