# Первичная онтология из odmkey (пайплайн для интеграции с ONTOL)

`build_primary_ontology.py`: находит все `\odmkey{name}{index}` (сущность `definition`
в AST), группирует их по окну из 2 соседних `semantic_block`, для каждой пары понятий
в окне классифицирует тип связи шаблонами (задача 3.2), сравнивает с
`data/pairs_w_relation.json` (дискретка). При конфликте побеждает дискретка.

- `data/ontology_errors.jsonl` — датасет ошибок: `mismatch` (не совпало с дискреткой),
  `novel` (нашёл, чего нет в дискретке), `missed` (есть в дискретке, не нашёл).
- `data/ontology_final.json` — итоговая онтология (дискретка + новые пары от DiGr).

## Известное ограничение

Индекс `\odmkey` — не то же самое, что имя в `pairs_w_relation.json` (там короче и без
англ. глосс: `"Область (domain)!интерпретации (of interpretation)"` vs `"Область
интерпретации"`). После очистки (`clean_index`) точное совпадение — 118/307 уникальных
имён дискретки. Остальное требует нечёткого сопоставления, для этого в проекте уже
есть `resolve_ontology.py` (помечен как legacy) — не переделывал его сейчас.

## Запуск

```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt
PYTHONPATH=src PYTHONIOENCODING=utf-8 .venv/Scripts/python build_primary_ontology.py
PYTHONPATH=src .venv/Scripts/python -m pytest -q tests/
```
