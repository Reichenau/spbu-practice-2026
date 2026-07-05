#!/usr/bin/env python
"""ontology_final.json -> простой .tdl (ONTOL V3) для ONTOL: КЛАСС на понятие + связи.

Синтаксис по исходникам ONTOL V3 (uml_dsl/tdl_lexer.py, examples/*.tdl):
generalization -> ОБОБЩЕНИЕ A -> B; dependency -> ЗАВИСИМОСТЬ A -> B;
остальное (aggregation/composition/association/input/output/instance/manifest) ->
АССОЦИАЦИЯ с ИМЯ "<тип>" - явного текстового синтаксиса для ромба
агрегации/композиции в лексере не нашёл, поэтому не выдумываю, просто помечаю именем.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def safe_class_name(name: str) -> str:
    cleaned = re.sub(r"[^0-9A-Za-zА-Яа-яЁё]+", "_", name).strip("_")
    return cleaned or "Concept"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Онтология -> TDL")
    parser.add_argument("--ontology", default="data/ontology_final.json")
    parser.add_argument("--out", default="data/ontology.tdl")
    args = parser.parse_args(argv)

    pairs = json.loads(Path(args.ontology).read_text(encoding="utf-8"))
    names: set[str] = set()
    for pr in pairs:
        names.add(pr["name1"])
        names.add(pr["name2"])
    class_of = {n: safe_class_name(n) for n in names}

    lines = ["-- Первичная онтология из DiGr, автогенерация build_tdl.py"]
    for n in sorted(names):
        lines += [f"КЛАСС {class_of[n]}", f"-- {n}", "КОНЕЦ КЛАСС", ""]

    for pr in pairs:
        a, b, t = class_of[pr["name1"]], class_of[pr["name2"]], pr["type"].lower()
        if t == "generalization":
            lines.append(f"ОБОБЩЕНИЕ {a} -> {b}")
        elif t == "dependency":
            lines.append(f"ЗАВИСИМОСТЬ {a} -> {b}")
        else:
            lines += ["АССОЦИАЦИЯ", f"  {a} *", "  --", f"  {b} *", f'  ИМЯ "{t}"', ""]

    Path(args.out).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"-> {args.out} ({len(names)} классов, {len(pairs)} связей)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
