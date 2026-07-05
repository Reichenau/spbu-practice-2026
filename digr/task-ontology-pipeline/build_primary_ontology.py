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
    DEFAULT_CUE_WORDS,
    BlockIndex,
    ConceptOccurrence,
    concept_regex,
    count_cues,
    extract_chunk,
    find_candidates_text,
    load_document,
    load_semantic_blocks,
    score_candidate,
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


# см. relation_matcher/README.md - Inheritance -> generalization не опечатка
LABEL_MAP = {
    "aggregation": "aggregation", "association": "association", "composition": "composition",
    "dependency": "dependency", "inheritance": "generalization", "input": "input",
    "instance": "instance", "manifest": "manifest", "output": "output",
}


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


def chunk_by_text_search(engine, document, full_text: str, block_index: BlockIndex, name_a: str, name_b: str) -> str | None:
    # тот же поиск, что и build_chunks_dataset.py: по словоформам в тексте,
    # а не по позиции odmkey - odmkey ставится один раз, а слово в тексте
    # встречается многократно, поэтому так находится намного больше пар.
    candidates = find_candidates_text(engine, document, full_text, block_index, name_a, name_b, window_blocks=2)
    if not candidates:
        return None
    re_a = re.compile(concept_regex(name_a), re.IGNORECASE)
    re_b = re.compile(concept_regex(name_b), re.IGNORECASE)
    scored = []
    for cand in candidates:
        chunk, _ = extract_chunk(full_text, cand.occ_a, cand.occ_b, re_a, re_b, block_index, max_chunk_chars=1000, no_clean=False)
        if chunk:
            scored.append((score_candidate(cand, count_cues(chunk, DEFAULT_CUE_WORDS)), chunk))
    if not scored:
        return None
    return max(scored, key=lambda t: t[0])[1]


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

    ground_truth = load_ground_truth(args.pairs)
    classifier = TemplateRelationClassifier(args.templates, args.config_dir, engine=engine)

    errors: list[dict] = []
    final: list[dict] = []
    covered_names: set[frozenset[str]] = set()

    # шаг 1: известные пары дискретки - проверенный текстовый поиск (даёт ~372/414,
    # а не ~24 как поиск по позиции odmkey, см. README)
    for (name1, name2), gt_type in ground_truth.items():
        chunk = chunk_by_text_search(engine, document, full_text, block_index, name1, name2)
        covered_names.add(frozenset({name1, name2}))
        if not chunk:
            errors.append({"index_a": name1, "index_b": name2, "ground_truth_type": gt_type, "status": "missed"})
            continue
        predicted = classifier.predict(to_plain_word(name1), to_plain_word(name2), chunk)
        record = {"index_a": name1, "index_b": name2, "predicted_relation_type": predicted,
                   "ground_truth_type": gt_type, "reference_chunk": chunk}
        if predicted.lower() != LABEL_MAP.get(gt_type.lower(), gt_type.lower()):
            record["status"] = "mismatch"
            errors.append(record)
        final.append({"name1": name1, "name2": name2, "type": gt_type})

    # шаг 2: новые пары вне дискретки - по совместной встречаемости odmkey
    # (полный текстовый перебор всех ~1465 понятий тут не потянуть, см. README)
    candidates = pairs_within_blocks(odmkeys, block_index)
    candidates = {(a, b) for a, b in candidates if frozenset({a, b}) not in covered_names}
    print(f"  новых кандидатных пар (odmkey, вне дискретки): {len(candidates)}")

    for index_a, index_b in sorted(candidates):
        chunk = build_reference_chunk(full_text, index_a, index_b, odmkeys, block_index)
        if not chunk:
            continue
        predicted = classifier.predict(to_plain_word(index_a), to_plain_word(index_b), chunk)
        errors.append({"index_a": index_a, "index_b": index_b, "predicted_relation_type": predicted,
                        "reference_chunk": chunk, "status": "novel"})
        final.append({"name1": index_a, "name2": index_b, "type": predicted})

    Path(args.errors_out).write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in errors) + "\n", encoding="utf-8",
    )
    Path(args.final_out).write_text(json.dumps(final, ensure_ascii=False, indent=2), encoding="utf-8")

    n_mismatch = sum(1 for r in errors if r.get("status") == "mismatch")
    n_novel = sum(1 for r in errors if r.get("status") == "novel")
    n_missed = sum(1 for r in errors if r.get("status") == "missed")
    n_matched = len(ground_truth) - n_missed
    print(f"дискретка: найдено {n_matched}/{len(ground_truth)}, из них верно {n_matched - n_mismatch}, mismatch={n_mismatch}, missed={n_missed}")
    print(f"novel={n_novel}")
    print(f"-> {args.errors_out}, {args.final_out} ({len(final)} пар)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
