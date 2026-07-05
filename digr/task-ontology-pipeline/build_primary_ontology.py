#!/usr/bin/env python
"""odmkey -> первичная онтология через DiGr -> сравнение с дискреткой -> датасет ошибок.

1. FIND definition (все \\odmkey{name}{index}) через DSL, группировка по semantic_block.
2. Внутри каждого блока - все пары различных понятий, встретившихся вместе.
3. Тип связи - TemplateRelationClassifier (задача 3.2).
4. Сравнение с pairs_w_relation.json (дискретка): при конфликте побеждает дискретка.
   Что нашёл DiGr, чего нет в дискретке - "novel". Что есть в дискретке, но DiGr
   не нашёл - "missed". Всё вместе - data/ontology_errors.jsonl.
5. Итоговая (исправленная) онтология - data/ontology_final.json.

Запуск: python build_primary_ontology.py --tex data/all_lectures.tex \
    --pairs data/pairs_w_relation.json --config-dir config/formats
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from itertools import combinations
from pathlib import Path

_SRC = Path(__file__).resolve().parent / "src"
if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from dsl import ActorDslEngine  # noqa: E402

from build_chunks_dataset import (  # noqa: E402
    BlockIndex,
    ConceptOccurrence,
    concept_regex,
    extract_chunk,
    load_document,
    load_semantic_blocks,
    to_plain_word,
)
from relation_templates import TemplateRelationClassifier  # noqa: E402


def clean_index(index: str) -> str:
    # снимает англ. глоссы "(...)" и "!"-иерархию odmkey, чтобы совпадало
    # с простыми именами из pairs_w_relation.json ("Область (domain)!интерпретации
    # (of interpretation)" -> "Область интерпретации")
    index = re.sub(r"\s*\([^)]*\)", "", index)
    return index.replace("!", " ").strip()


def load_odmkeys(engine: ActorDslEngine, document) -> list[ConceptOccurrence]:
    result = engine.execute(document, "FIND definition RETURN nodes").to_dict()
    out: list[ConceptOccurrence] = []
    for item in result["items"]:
        node = item["nodes"]
        meta = node.get("metadata", {})
        index = clean_index(meta.get("index") or meta.get("name") or "")
        if not index:
            continue
        out.append(ConceptOccurrence(index=index, name=meta.get("name", index), start=node["start"], end=node["end"]))
    return out


def pairs_within_blocks(odmkeys: list[ConceptOccurrence], block_index: BlockIndex, window_blocks: int = 2) -> set[tuple[str, str]]:
    # то же окно в 2 соседних semantic_block, что и build_chunks_dataset.py,
    # а не только один блок - иначе почти нет пересечения с дискреткой.
    by_block: dict[int, list[ConceptOccurrence]] = {}
    for occ in odmkeys:
        block = block_index.index_of(occ.start)
        if block is None:
            continue
        by_block.setdefault(block, []).append(occ)

    candidates: set[tuple[str, str]] = set()
    max_block = max(by_block, default=-1)
    for start in range(max_block + 1):
        indices: set[str] = set()
        for b in range(start, min(start + window_blocks, max_block + 1)):
            indices.update(o.index for o in by_block.get(b, ()))
        for a, b in combinations(sorted(indices), 2):
            candidates.add((a, b))
    return candidates


def load_ground_truth(path: str) -> dict[tuple[str, str], str]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return {(item["name1"], item["name2"]): item["type"] for item in data}


def build_reference_chunk(full_text: str, index_a: str, index_b: str, odmkeys: list[ConceptOccurrence], block_index: BlockIndex) -> str | None:
    occs_a = [o for o in odmkeys if o.index == index_a]
    occs_b = [o for o in odmkeys if o.index == index_b]
    if not occs_a or not occs_b:
        return None
    re_a = re.compile(concept_regex(index_a), re.IGNORECASE)
    re_b = re.compile(concept_regex(index_b), re.IGNORECASE)
    best_chunk, best_len = None, None
    for occ_a in occs_a:
        for occ_b in occs_b:
            chunk, _ = extract_chunk(full_text, occ_a, occ_b, re_a, re_b, block_index, max_chunk_chars=1000, no_clean=False)
            if chunk and (best_len is None or len(chunk) < best_len):
                best_chunk, best_len = chunk, len(chunk)
    return best_chunk


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Первичная онтология из odmkey через DiGr")
    parser.add_argument("--tex", default="data/all_lectures.tex")
    parser.add_argument("--pairs", default="data/pairs_w_relation.json")
    parser.add_argument("--config-dir", default="config/formats")
    parser.add_argument("--templates", default="templates.yaml")
    parser.add_argument("--errors-out", default="data/ontology_errors.jsonl")
    parser.add_argument("--final-out", default="data/ontology_final.json")
    args = parser.parse_args(argv)

    document = load_document(args.tex, args.config_dir)
    full_text = document.root.text
    engine = ActorDslEngine()

    print("Ищу semantic_block ...")
    blocks = load_semantic_blocks(engine, document)
    block_index = BlockIndex(blocks)

    print("Ищу odmkey (definition) ...")
    odmkeys = load_odmkeys(engine, document)
    print(f"  odmkey: {len(odmkeys)}, semantic_block: {len(blocks)}")

    candidates = pairs_within_blocks(odmkeys, block_index)
    print(f"  кандидатных пар (совместно в одном блоке): {len(candidates)}")

    ground_truth = load_ground_truth(args.pairs)
    classifier = TemplateRelationClassifier(args.templates, args.config_dir, engine=engine)

    errors: list[dict] = []
    final: list[dict] = []
    matched_gt: set[tuple[str, str]] = set()

    for index_a, index_b in sorted(candidates):
        chunk = build_reference_chunk(full_text, index_a, index_b, odmkeys, block_index)
        if not chunk:
            continue
        predicted = classifier.predict(to_plain_word(index_a), to_plain_word(index_b), chunk)

        gt_type = ground_truth.get((index_a, index_b))
        gt_key = (index_a, index_b)
        if gt_type is None:
            gt_type = ground_truth.get((index_b, index_a))
            gt_key = (index_b, index_a)

        record = {"index_a": index_a, "index_b": index_b, "predicted_relation_type": predicted, "reference_chunk": chunk}
        if gt_type is not None:
            matched_gt.add(gt_key)
            record["ground_truth_type"] = gt_type
            if predicted.lower() != gt_type.lower():
                record["status"] = "mismatch"
                errors.append(record)
            final.append({"name1": gt_key[0], "name2": gt_key[1], "type": gt_type})
        else:
            record["status"] = "novel"
            errors.append(record)
            final.append({"name1": index_a, "name2": index_b, "type": predicted})

    for (name1, name2), gt_type in ground_truth.items():
        if (name1, name2) not in matched_gt:
            errors.append({"index_a": name1, "index_b": name2, "ground_truth_type": gt_type, "status": "missed"})

    Path(args.errors_out).write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in errors) + "\n", encoding="utf-8",
    )
    Path(args.final_out).write_text(json.dumps(final, ensure_ascii=False, indent=2), encoding="utf-8")

    n_mismatch = sum(1 for r in errors if r.get("status") == "mismatch")
    n_novel = sum(1 for r in errors if r.get("status") == "novel")
    n_missed = sum(1 for r in errors if r.get("status") == "missed")
    print(f"mismatch={n_mismatch} novel={n_novel} missed={n_missed}")
    print(f"-> {args.errors_out}, {args.final_out} ({len(final)} пар)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
