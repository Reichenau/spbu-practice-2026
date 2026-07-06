# Задание 3.1 — объединение типов запросов DiGr DSL

- `dsl_report.pdf` — отчёт.
- `main.py` — CLI, строит AST документа и даёт интерактивный DSL-запрос.
- `../engine/src/dsl/model/query_ast.py` (единый `Query`), `../engine/src/dsl/parsing/`
  (единый парсер), `../engine/src/dsl/execution/query_results.py` (единый
  `DslQueryExecutionResult`), `../engine/src/dsl/execution/query_validator.py`
  (семантические ограничения по `kind`) — движок, общий с task-3-2 и
  task-ontology-pipeline, см. [`../engine`](../engine).
- `tests/` — тесты DSL и интеграционные тесты, адаптированные под единую модель.
- `config/`, `text.txt`, `GA_1_2025.tex` — тестовые данные и конфигурация форматов,
  нужны тестам и не изменялись.

## Запуск тестов


```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt -r requirements-dev.txt
PYTHONPATH=../engine/src .venv/Scripts/python -m pytest -q
```

Единственный ожидаемый непройденный тест — `test_cli_noninteractive_smoke_outputs_ast_json`:
он падает из-за кодировки консоли Windows (`cp1252`) при выводе кириллицы в `main.py`,
это не связано с DSL и не менялось в этой задаче. Тест запускает `python main.py`
(раньше — `python src/main.py`, до выноса движка в `../engine`).

