# Funcionamiento de la aplicación

## Instalar y arrancar

Crea un entorno virtual local, instala `requirements.txt` y ejecuta `python main.py`. Para validar el motor y la aplicación usa `python -m pytest -q`.

## Vistas

1. **Reconocedor:** procesa tokens, resultado sintáctico y valor calculado.
2. **Gramática:** muestra producciones y FOLLOW de cada no terminal.
3. **Autómata LR:** representa estados como nodos y sus transiciones etiquetadas; debajo lista origen, símbolo y destino.
4. **ACTION/GOTO:** expone las celdas que el generador calculó.
5. **Simulación:** muestra pila de estados/símbolos, entrada pendiente, acción, regla y explicación. Siguiente/Anterior recorren la traza; Ejecutar y Reiniciar avanzan o vuelven al inicio.
6. **Árbol sintáctico:** visualiza el AST creado en las reducciones.
7. **Banco de pruebas:** ejecuta 15 cadenas válidas y 15 inválidas sobre el mismo servicio de la interfaz.

## Alcance del evaluador

Se calculan expresiones de literales enteros y decimales, paréntesis y operaciones binarias. Las asignaciones como `var = 2 + 3` entregan `("var", 5.0)`. Un identificador usado como operando necesita un entorno de variables, no incluido en el alcance inicial, por lo que la evaluación informa el error explícitamente.

El ejemplo `var = 5.0 + 7.0 * (3.0 + 8.0 / 4.0)` entrega `var = 40.0`: primero `8.0 / 4.0 = 2.0`, después `(3.0 + 2.0) = 5.0`, luego `7.0 * 5.0 = 35.0` y finalmente `5.0 + 35.0 = 40.0`.
