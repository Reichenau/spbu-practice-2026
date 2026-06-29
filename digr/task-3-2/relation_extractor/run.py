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

from document_ast import ActorAstParser
from relation_extractor import PatternBasedRelationExtractor
import yaml


def main():
    parser = argparse.ArgumentParser(description="Извлечение отношений по шаблонам")
    parser.add_argument("--tex", required=True, help="Путь к TeX-файлу")
    parser.add_argument("--format", default=None, help="Формат (если не указан, определяется по расширению)")
    parser.add_argument("--config-dir", default="config/formats", help="Директория конфигов форматов")
    parser.add_argument("--templates", default="relation_extractor/templates.yaml", help="Файл с шаблонами")
    parser.add_argument("--out", default="relations.json", help="Выходной JSON-файл")
    parser.add_argument("--entity", default="definition", help="Сущность AST для извлечения терминов (например, definition)")
    args = parser.parse_args()

    # 1. Парсим документ
    print(f"Парсинг документа {args.tex}...")
    parser_doc = ActorAstParser.from_config_dir(args.config_dir)
    document = parser_doc.parse(args.tex, format_name=args.format)

    # 2. Загружаем шаблоны
    with open(args.templates, "r", encoding="utf-8") as f:
        templates = yaml.safe_load(f)

    # 3. Извлекаем отношения
    print("Извлечение отношений...")
    extractor = PatternBasedRelationExtractor(templates)

    # Если нужны термины из AST-сущностей:
    relations = extractor.extract_using_ast_entities(document, entity_name=args.entity)

    # Альтернативно, можно передать список терминов вручную:
    # terms = ["термин1", "термин2", ...]
    # relations = extractor.extract(document, terms)

    # 4. Сохраняем результат
    print(f"Найдено {len(relations)} отношений")
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(relations, f, ensure_ascii=False, indent=2)

    print(f"Результат сохранён в {args.out}")


if __name__ == "__main__":
    main()