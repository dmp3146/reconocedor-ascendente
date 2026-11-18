# Algoritmo ascendente SLR(1)

## Elección

SLR(1) es adecuado para esta gramática didáctica: genera la colección canónica LR(0) y restringe las reducciones con FOLLOW. Así se demuestra explícitamente cómo se construyen el autómata y las tablas, sin necesitar el mayor número de estados/lookaheads del LR(1) canónico. La gramática concreta genera una tabla sin conflictos; si se amplía con producciones conflictivas, el generador falla con estado, terminal y acciones en conflicto.

## Construcción

1. Se agrega `S' → S`.
2. `CLOSURE(I)` agrega los ítems `B → ·γ` cuando el punto precede al no terminal `B`.
3. `GOTO(I, X)` desplaza el punto sobre `X` y vuelve a aplicar CLOSURE.
4. Desde `{S' → ·S}` se exploran todos los símbolos alcanzables y se identifican estados por sus conjuntos de ítems.
5. Un ítem con punto antes de terminal `a` genera `ACTION[i,a] = SHIFT j`.
6. Un ítem completo `A → α·` genera REDUCE por esa producción en cada terminal de FOLLOW(A).
7. El ítem completo aumentado genera ACCEPT ante `$`; las transiciones por no terminal forman GOTO.

## FIRST/FOLLOW

La gramática no contiene epsilon. FIRST se propaga desde el primer símbolo de cada producción. FOLLOW agrega el FIRST del símbolo siguiente y, en el extremo, el FOLLOW del lado izquierdo hasta alcanzar punto fijo.

## Ejecución del parser

El parser mantiene una pila de estados (inicialmente `0`), una pila de símbolos/nodos y un cursor sobre tokens con marcador `$`.

- **SHIFT:** consume un token, crea una hoja AST y apila símbolo y estado destino.
- **REDUCE:** retira tantos símbolos como tenga el lado derecho, crea un nodo padre, consulta GOTO y apila el no terminal reducido.
- **ACCEPT:** termina con el AST raíz.
- Una celda ACTION ausente produce error sintáctico con ubicación y terminales esperados.

La traza registra el estado de pila y entrada restante antes de cada acción. Los números de estado y las celdas se derivan en ejecución, no se inventan. El evaluador aplica la precedencia de la estructura del AST; para el ejemplo `var = 5.0 + 7.0 * (3.0 + 8.0 / 4.0)`, el resultado matemáticamente correcto es `var = 40.0`.
