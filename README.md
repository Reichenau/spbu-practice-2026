# digr-practice

Летняя практика по DiGr — DSL для запросов к тексту, используется как часть
онтологической системы ONTOL.

- [`digr/task-1`](digr/task-1) — формальная грамматика DSL в РБНФ.
- [`digr/task-2`](digr/task-2) — описание архитектуры DiGr DSL.
- [`digr/engine`](digr/engine) — общий код DSL/AST/акторного рантайма, вышедший
  из задачи 3.1, используют task-3-1, task-3-2 и task-ontology-pipeline.
- [`digr/task-3-1`](digr/task-3-1) — объединение FIND/CONTEXT/DISTANCE в один тип
  запроса и единый AST.
- [`digr/task-3-2`](digr/task-3-2) — замена нейросетевой классификации связей на
  синтаксические шаблоны, эксперимент на корпусе дискретной математики.
- [`digr/task-ontology-pipeline`](digr/task-ontology-pipeline) — первичная
  онтология из `\odmkey` через DiGr, сравнение с эталоном (дискреткой), датасет
  ошибок, TDL-файлы по разделам для ONTOL.
