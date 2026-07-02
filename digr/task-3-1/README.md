# Задание 3.1 — объединение типов запросов DiGr DSL

- `dsl_report.pdf` — отчёт.
- `src/` — код: `src/dsl/model/query_ast.py` (единый `Query`), `src/dsl/parsing/` (единый
  парсер), `src/dsl/execution/query_results.py` (единый `DslQueryExecutionResult`),
  `src/dsl/execution/query_validator.py` (семантические ограничения по `kind`).
- `tests/` — тесты DSL и интеграционные тесты, адаптированные под единую модель.
- `config/`, `text.txt`, `GA_1_2025.tex` — тестовые данные и конфигурация форматов,
  нужны тестам и не изменялись.

## Запуск тестов


```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt -r requirements-dev.txt
PYTHONPATH=src .venv/Scripts/python -m pytest -q
```

Единственный ожидаемый непройденный тест — `test_cli_noninteractive_smoke_outputs_ast_json`:
он падает из-за кодировки консоли Windows (`cp1252`) при выводе кириллицы в `main.py`,
это не связано с DSL и не менялось в этой задаче.

