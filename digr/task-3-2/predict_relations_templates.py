#!/usr/bin/env python
"""predict_relations_templates.py — замена relation_matcher/predict_relations.py.

Тот же контракт CLI (--chunks/--out/--inplace, пишет predicted_relation_type
рядом с истинным relation_type), но вместо RuBERT — TemplateRelationClassifier
из relation_templates.py. Шаг A (build_chunks_dataset.py, DSL CONTEXT по всему
документу) и шаг C (load_qdrant.py) не меняются и не запускаются отсюда.

Запуск:
    python predict_relations_templates.py --chunks data/chunks_ontology_text_reference.jsonl \
        --out data/chunks_ontology_text_templates.jsonl --config-dir config/formats
"""
from __future__ import annotations

import argparse
import json
from collections import Counter

from relation_templates import TemplateRelationClassifier


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Проставить тип связи парам понятий синтаксическими шаблонами")
    parser.add_argument("--chunks", default="data/chunks_ontology_text_reference.jsonl")
    parser.add_argument("--out", default="data/chunks_ontology_text_templates.jsonl")
    parser.add_argument("--inplace", action="store_true", help="перезаписать --chunks вместо записи в --out")
    parser.add_argument("--templates", default="templates.yaml")
    parser.add_argument("--config-dir", default="config/formats")
    args = parser.parse_args(argv)

    with open(args.chunks, encoding="utf-8") as f:
        records = [json.loads(line) for line in f if line.strip()]

    classifier = TemplateRelationClassifier(args.templates, args.config_dir)

    dist: Counter = Counter()
    for i, rec in enumerate(records, start=1):
        label = classifier.predict(rec["concept_a"], rec["concept_b"], rec["reference_chunk"])
        rec["predicted_relation_type"] = label
        dist[label] += 1
        if i % 50 == 0:
            print(f"  {i}/{len(records)}")

    out_path = args.chunks if args.inplace else args.out
    with open(out_path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print(f"Размечено пар: {len(records)}")
    print(f"Распределение предсказанных типов: {dict(dist)}")
    print(f"-> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
