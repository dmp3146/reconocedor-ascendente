# Informe de código completo

## Objetivo

Implementar un reconocedor ascendente que permita observar el proceso formal de análisis de expresiones y asignaciones, junto con un árbol sintáctico y un evaluador restringido.

## Componentes

`lexer/tokens.py` define tipos y tokens posicionados. `lexer/lexer.py` recorre el texto e informa caracteres y decimales mal formados. `grammar/grammar.py` representa la gramática aumentada, indexa producciones y calcula FIRST/FOLLOW. `parsers/ascending/slr.py` implementa LRItem, CLOSURE, GOTO, colección canónica LR(0), ACTION, GOTO y detección de conflictos. `parsers/ascending/parser.py` ejecuta la tabla y crea nodos AST en cada reducción. `evaluator/evaluator.py` evalúa el árbol sin interpretar cadenas como código. `services/analyzer_service.py` conecta estos módulos. `app/` presenta sus datos en siete vistas.

## Propiedades demostrables

- La precedencia se deriva de `E`, `T` y `F`; los operadores de cada nivel son asociativos por la izquierda.
- La asignación es sintaxis de `S`, no una expresión aritmética.
- Toda transición del autómata sale de GOTO calculado sobre ítems.
- Toda reducción de la tabla está limitada por FOLLOW del no terminal reducido.
- La evaluación recibe un AST y no emplea `eval()` ni `exec()`.
- La interfaz comparte el motor y la tabla real; no usa una simulación independiente.

## Verificación

`tests/test_lexer.py` cubre tokens, posiciones y errores. `tests/test_grammar_slr.py` verifica producciones, FIRST/FOLLOW, CLOSURE, GOTO, autómata, clases de acción y conflictos. `tests/test_parser_evaluator.py` ejercita 15 entradas válidas, 15 inválidas, la traza, precedencia, AST y el ejemplo principal (`var = 40.0`).

## Limitaciones conocidas

No hay operadores unarios ni asignaciones encadenadas. Los identificadores se reconocen, pero no existe entorno de variables para leerlos durante evaluación. La vista del autómata es una visualización educativa compacta y puede tener aristas cruzadas en grafos más grandes.
