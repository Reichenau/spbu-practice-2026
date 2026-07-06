# DiGr engine

Общий код, вышедший из задачи 3.1 (объединение FIND/CONTEXT/DISTANCE) и
используемый без изменений в task-3-2 и task-ontology-pipeline.

- `src/actor` — акторный рантайм (FSM, драйверы, почтовые ящики).
- `src/document_ast` — парсинг документа в AST.
- `src/dsl` — DSL: лексер, парсер, единая модель запроса и его исполнение.

Каждая задача подключает его через `PYTHONPATH=../engine/src` (см. README
соответствующей задачи). `config/formats/*.yaml` и `requirements.txt`
остаются в каждой задаче отдельно — это конфигурация запуска, а не код.
