# Funcionamiento de la aplicación

## Instalar y arrancar

Crea un entorno virtual local, instala `requirements.txt` y ejecuta `python main.py`. Para validar el motor y la aplicación usa `python -m pytest -q`.

El botón de la parte superior del menú lateral permite ocultarlo y ampliar el área de trabajo. El botón de la barra superior lo vuelve a mostrar sin cambiar la vista seleccionada ni perder el análisis.

## Vistas

1. **Reconocedor:** procesa tokens, resultado sintáctico y valor calculado.
2. **Gramática:** muestra producciones y FOLLOW de cada no terminal.
3. **Autómata LR:** muestra el autómata fijo generado por la gramática. Tras analizar una entrada, los controles recorren su traza real: SHIFT sigue una arista terminal, REDUCE desapila y sigue GOTO por el no terminal (sin consumir entrada), y ACCEPT o ERROR no generan aristas. Verde indica estados y transiciones visitados; naranja, el estado y la última transición actuales. Seleccionar un estado muestra sus ítems LR(0).
4. **ACTION/GOTO:** expone las celdas que el generador calculó.
5. **Simulación:** muestra pila de estados/símbolos, entrada pendiente, acción, regla y explicación. Siguiente/Anterior recorren la traza; Ejecutar y Reiniciar avanzan o vuelven al inicio.
6. **Árbol sintáctico:** visualiza el AST creado en las reducciones.
7. **Banco de pruebas:** ejecuta 15 cadenas válidas y 15 inválidas sobre el mismo servicio de la interfaz.

## Alcance del evaluador

Se calculan expresiones de literales enteros y decimales, paréntesis y operaciones binarias. Las asignaciones como `var = 2 + 3` entregan `("var", 5.0)`. Un identificador usado como operando necesita un entorno de variables, no incluido en el alcance inicial, por lo que la evaluación informa el error explícitamente.

El reconocedor distingue los estados léxico, sintáctico y de evaluación. Si hay división entre cero, la sintaxis sigue aceptada y el árbol y la traza hasta ACCEPT permanecen disponibles, pero la evaluación indica ERROR y el resultado final es NO EVALUABLE. Un error léxico impide ejecutar el parser; un error sintáctico impide evaluar.

El ejemplo `var = 5.0 + 7.0 * (3.0 + 8.0 / 4.0)` entrega `var = 40.0`: primero `8.0 / 4.0 = 2.0`, después `(3.0 + 2.0) = 5.0`, luego `7.0 * 5.0 = 35.0` y finalmente `5.0 + 35.0 = 40.0`.
