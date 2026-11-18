# Arquitectura

## Capas y responsabilidades

- `lexer/`: convierte caracteres en tokens con lexema y posición de línea/columna.
- `grammar/`: define producciones y calcula FIRST/FOLLOW.
- `parsers/ascending/`: calcula CLOSURE y GOTO, genera estados LR(0), transiciones y tabla SLR(1), y ejecuta SHIFT/REDUCE/ACCEPT.
- `evaluator/`: recorre el AST producido por reducciones; no interpreta texto ejecutable.
- `services/`: compone lexer, tabla, parser y evaluación.
- `app/`: ventana PySide6, navegación y siete vistas conectadas al servicio.
- `tests/`: pruebas del lexer, la gramática, tabla, parser, AST y evaluación.
- `docs/`: documentación técnica y guía de exposición.

La interfaz no contiene lógica de parsing. `AnalyzerService` crea la gramática y construye una sola tabla al iniciar; las vistas consultan ese mismo motor.

## Flujo de datos

```text
Texto → Lexer → Tokens → SLRParser (ACTION/GOTO) → AST → Evaluador
                                     └────────────→ traza de simulación
```

La gramática tiene 12 producciones contando la aumentada. La generación de tabla lanza `GrammarConflictError` si dos acciones incompatibles ocupan una misma celda.
