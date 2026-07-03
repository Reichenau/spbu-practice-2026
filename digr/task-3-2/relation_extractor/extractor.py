import re
import pymorphy3
from typing import List, Dict, Optional, Tuple

class PatternBasedRelationExtractor:
    def __init__(self, templates: Dict[str, List[str]], window_limit: int = 3,
                 max_distance_words: int = 20, use_lemmatization: bool = True):
        self.templates = templates
        self.window_limit = window_limit
        self.max_distance_words = max_distance_words
        self.use_lemmatization = use_lemmatization
        self.morph = pymorphy3.MorphAnalyzer() if use_lemmatization else None
        self.engine = ActorDslEngine()
        self.negative_words = {"не", "ни", "без"}

    def _normalize(self, text: str) -> str:
        if not self.use_lemmatization or not self.morph:
            return text.lower()
        words = re.findall(r'\w+', text)
        lemmas = []
        for w in words:
            parsed = self.morph.parse(w)
            if parsed:
                lemmas.append(parsed[0].normal_form)
        return " ".join(lemmas)

    def _check_negative(self, context: str) -> bool:
        # Проверяем наличие отрицательных слов до первого найденного термина или шаблона
        # Упрощённо: если есть "не" и рядом с ним один из терминов или шаблонов, то false
        # Пока просто проверяем наличие слов "не", "ни" в контексте
        for neg in self.negative_words:
            if neg in context.lower():
                # Если есть отрицание, проверяем, не относится ли оно к связи
                # Для простоты отбрасываем все окна с отрицанием (можно улучшить)
                return True
        return False

    def extract(self, document: AstDocument, terms: List[str]) -> List[Dict]:
        results = []
        for i, t1 in enumerate(terms):
            for t2 in terms[i+1:]:
                for rel_type, patterns in self.templates.items():
                    # Строим regex из шаблонов, экранируем
                    if self.use_lemmatization:
                        # Для лемматизации сохраняем исходные шаблоны, но ищем по леммам
                        # Мы не можем использовать regex в DSL, поэтому будем искать через текст
                        # В текущей версии DSL нельзя лемматизировать на лету, поэтому лучше искать
                        # по словам, используя побитовый поиск или использовать строки.
                        # Для простоты оставим обычный поиск строк, но добавим больше вариантов.
                        pass
                    pattern = "|".join(re.escape(p) for p in patterns)
                    query = f"""
                    CONTEXT sentence LIMIT {self.window_limit}
                    FOR "{t1}", "{t2}", /{pattern}/
                    RETURN window, matches
                    """
                    res = self.engine.execute(document, query)
                    if res.count > 0:
                        for item in res.to_dict()["items"]:
                            window_data = item["window"]
                            # Проверка расстояния между терминами
                            # Вычисляем количество слов между позициями терминов
                            # Но у нас нет позиций терминов, только текст окна.
                            # Можно найти позиции в тексте окна и подсчитать слова.
                            window_text = window_data["text"]
                            # Найдём позиции терминов и шаблона
                            # Если шаблон найден, то окно уже подходит
                            # Дополнительно можно проверить расстояние между терминами
                            # Просто проверяем, что в тексте есть оба термина и шаблон
                            # Это уже сделано в запросе.
                            # Добавим дополнительную проверку на отрицание
                            if self._check_negative(window_text):
                                continue
                            results.append({
                                "relation_type": rel_type,
                                "term1": t1,
                                "term2": t2,
                                "context": window_text,
                                "span": window_data["span"],
                            })
        # Удалить дубликаты (по паре, типу, контексту)
        seen = set()
        unique = []
        for r in results:
            key = (r["term1"], r["term2"], r["relation_type"], r["context"])
            if key not in seen:
                seen.add(key)
                unique.append(r)
        return unique