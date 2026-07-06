# digr-practice

Летняя практика по DiGr — DSL для запросов к тексту, используется как часть
онтологической системы ONTOL.

- [`digr/engine`](digr/engine) — DSL, AST и акторный рантайм.
- [`digr/relation-classifier`](digr/relation-classifier) — классификация связей
  между понятиями текстовыми шаблонами вместо нейросети.
- [`digr/ontology-pipeline`](digr/ontology-pipeline) — первичная онтология из
  `\odmkey` через DiGr, сравнение с эталоном (дискреткой), датасет ошибок,
  TDL-файлы по разделам для ONTOL.
- [`digr/data`](digr/data) — общий корпус (дискретная математика), используется
  и классификатором, и онтологическим пайплайном.
- [`digr/docs`](digr/docs) — грамматика DSL и отчёты.
