#!/usr/bin/env python
"""
Извлечение отношений по синтаксическим шаблонам с использованием DiGr DSL.

Запуск (из корня проекта):
    PYTHONPATH=src python relation_extractor/run.py --tex GA_1_2025.tex --format tex --out relations.json
"""

import argparse
import json
import sys
from pathlib import Path

# Добавляем src в путь
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import yaml
from document_ast import ActorAstParser
from relation_extractor import PatternBasedRelationExtractor


def main():
    parser = argparse.ArgumentParser(description="Извлечение отношений по шаблонам")
    parser.add_argument("--tex", required=True, help="Путь к TeX-файлу")
    parser.add_argument("--format", default=None, help="Формат (если не указан, определяется по расширению)")
    parser.add_argument("--config-dir", default="config/formats", help="Директория конфигов форматов")
    parser.add_argument("--templates", default="relation_extractor/templates.yaml", help="Файл с шаблонами")
    parser.add_argument("--out", default="relations.json", help="Выходной JSON-файл")
    parser.add_argument("--entity", default="definition", help="Сущность AST для извлечения терминов (например, definition)")
    parser.add_argument("--window-limit", type=int, default=3, help="Количество предложений в окне (по умолчанию 3)")
    parser.add_argument("--max-distance", type=int, default=20, help="Максимальное количество слов между терминами (пока не используется)")
    parser.add_argument("--no-negation-filter", action="store_true", help="Отключить фильтрацию отрицаний")
    parser.add_argument("--debug", action="store_true", help="Выводить отладочную информацию")
    args = parser.parse_args()

    # 1. Парсим документ
    print(f"Парсинг документа {args.tex}...")
    parser_doc = ActorAstParser.from_config_dir(args.config_dir)
    document = parser_doc.parse(args.tex, format_name=args.format)

    # 2. Загружаем шаблоны
    with open(args.templates, "r", encoding="utf-8") as f:
        templates = yaml.safe_load(f)

    # 3. Создаём экстрактор с параметрами
    extractor = PatternBasedRelationExtractor(
        templates,
        window_limit=args.window_limit,
        max_distance=args.max_distance,
        negation_filter=not args.no_negation_filter,
        debug=args.debug,
    )

    # 4. Извлекаем отношения
    print("Извлечение отношений...")
    relations = extractor.extract_using_ast_entities(document, entity_name=args.entity)

    # 5. Сохраняем результат
    print(f"Найдено {len(relations)} отношений")
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(relations, f, ensure_ascii=False, indent=2)

    print(f"Результат сохранён в {args.out}")


if __name__ == "__main__":
    main()