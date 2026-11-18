# Reconocedor Ascendente

Prototipo educativo de análisis sintáctico ascendente SLR(1), implementado desde cero con Python y PySide6. La tabla ACTION/GOTO y el autómata se generan a partir de la gramática; no se usan tablas codificadas ni `eval()`/`exec()`.

## Requisitos e instalación

Se requiere Python 3.10 o posterior. Desde la carpeta del proyecto:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Ejecución y pruebas

```powershell
python main.py
python -m pytest -q
```

La ventana contiene siete vistas: reconocedor, gramática, autómata LR, tabla ACTION/GOTO, simulación, árbol sintáctico y banco de pruebas. Un identificador como `x` se reconoce, pero no se evalúa si no hay valor asignado; el evaluador solo conoce literales numéricos y asignaciones sin entorno externo.

El ejemplo `var = 5.0 + 7.0 * (3.0 + 8.0 / 4.0)` se evalúa como `var = 40.0`, respetando precedencia convencional y paréntesis.

## Gramática inicial

```text
S' → S
S  → id = E | E
E  → E + T | E - T | T
T  → T * F | T / F | F
F  → ( E ) | id | num
```

Consulta [docs/arquitectura.md](docs/arquitectura.md), [docs/funcionamiento.md](docs/funcionamiento.md), [docs/algoritmo_ascendente.md](docs/algoritmo_ascendente.md) y [docs/informe_codigo_completo.md](docs/informe_codigo_completo.md) para el detalle técnico.
