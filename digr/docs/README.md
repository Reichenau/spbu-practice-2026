# Отчёты и грамматика

- `original_dsl_grammar.rbnf`, `grammar_report.pdf` — исходная грамматика DSL
  в РБНФ: FIND/CONTEXT/DISTANCE как три отдельные продукции, с валидацией
  (маппинг правил на код).
- `architecture_report.pdf`/`.tex` — архитектура DiGr DSL: подсистемы, слои,
  типы запросов (до объединения).
- `dsl_unification_report.pdf` — объединение FIND/CONTEXT/DISTANCE в один тип
  запроса и единый AST; актуальная грамматика после объединения лежит в
  [`../engine/dsl_grammar.rbnf`](../engine/dsl_grammar.rbnf), а не здесь.
- `relation_classifier_report.pdf`/`.tex` — синтаксические шаблоны вместо
  нейросети для классификации связей, эксперимент на корпусе дискретной
  математики: честная сверка метрик нейросети с `holdout_metrics.json`,
  почему Input/Output неразличимы по тексту, откуда взяты шаблоны, разбор
  результатов по классам.
