from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor, QFont, QPen
from PySide6.QtWidgets import (
    QGraphicsEllipseItem,
    QGraphicsLineItem,
    QGraphicsScene,
    QGraphicsTextItem,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QTableWidget,
    QTableWidgetItem,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from evaluator.evaluator import EvaluationError, evaluate
from lexer.lexer import LexerError
from parsers.ascending.parser import ParseError, TraceStep
from services.analyzer_service import Analysis, AnalyzerService


class RecognizerView(QWidget):
    def __init__(self, service: AnalyzerService, on_analysis):
        super().__init__()
        self.service = service
        self.on_analysis = on_analysis
        layout = QVBoxLayout(self)
        layout.addWidget(_title("Reconocedor de expresiones"))
        layout.addWidget(QLabel("Escribe una expresión o asignación compatible:"))
        self.source = QPlainTextEdit()
        self.source.setPlaceholderText("var = 5.0 + 7.0 * (3.0 + 8.0 / 4.0)")
        self.source.setMaximumHeight(110)
        self.source.setPlainText("var = 5.0 + 7.0 * (3.0 + 8.0 / 4.0)")
        layout.addWidget(self.source)
        self.analyze_button = QPushButton("Analizar y evaluar")
        self.analyze_button.clicked.connect(self.analyze)
        layout.addWidget(self.analyze_button, alignment=Qt.AlignmentFlag.AlignLeft)
        self.tokens = QLabel()
        self.tokens.setWordWrap(True)
        self.result = QLabel("La aplicación construirá un AST y aplicará el parser SLR(1).")
        self.result.setObjectName("result")
        self.result.setWordWrap(True)
        layout.addWidget(self.tokens)
        layout.addWidget(self.result)
        layout.addStretch()

    def analyze(self) -> None:
        try:
            analysis = self.service.analyze(self.source.toPlainText())
        except (LexerError, ParseError, EvaluationError, ZeroDivisionError) as error:
            self.tokens.setText("")
            self.result.setText(f"❌ Entrada rechazada: {error}")
            self.result.setProperty("valid", False)
            self.result.style().unpolish(self.result)
            self.result.style().polish(self.result)
            self.on_analysis(None)
            return
        self.tokens.setText("Tokens:  " + "   ".join(str(token) for token in analysis.tokens))
        self.result.setText(
            "✅ Cadena aceptada por SLR(1).  "
            + (f"{analysis.variable} = " if analysis.variable else "Resultado = ")
            + str(analysis.value)
        )
        self.result.setProperty("valid", True)
        self.result.style().unpolish(self.result)
        self.result.style().polish(self.result)
        self.on_analysis(analysis)


class GrammarView(QWidget):
    def __init__(self, service: AnalyzerService):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(_title("Gramática y producciones"))
        layout.addWidget(QLabel("Gramática aumentada utilizada para generar el autómata:"))
        grammar = service.table.grammar
        table = QTableWidget(len(grammar.productions), 3)
        table.setHorizontalHeaderLabels(["#", "Producción", "FOLLOW(lhs)"])
        for row, production in enumerate(grammar.productions):
            table.setItem(row, 0, _cell(str(production.index)))
            table.setItem(row, 1, _cell(str(production)))
            follow = service.table.follow.get(production.lhs, set())
            table.setItem(row, 2, _cell(", ".join(sorted(follow))))
        table.horizontalHeader().setStretchLastSection(True)
        table.resizeColumnsToContents()
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(table)
        layout.addWidget(
            QLabel(
                "La precedencia resulta de los niveles E (+, −), T (×, ÷) y F "
                "(paréntesis/átomos); las producciones recursivas a la izquierda "
                "establecen asociatividad por la izquierda."
            )
        )


class AutomatonView(QWidget):
    def __init__(self, service: AnalyzerService):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(_title("Autómata LR(0)"))
        layout.addWidget(
            QLabel("Estados generados por CLOSURE/GOTO; las aristas muestran transiciones.")
        )
        self.scene = QGraphicsScene(self)
        self.graph = QGraphicsView(self.scene)
        self.graph.setMinimumHeight(460)
        self.graph.setRenderHint(self.graph.renderHints())
        layout.addWidget(self.graph, 1)
        table = QTableWidget(len(service.table.transitions), 3)
        table.setHorizontalHeaderLabels(["Estado origen", "Símbolo", "Estado destino"])
        for row, ((source, symbol), target) in enumerate(
            sorted(service.table.transitions.items())
        ):
            table.setItem(row, 0, _cell(str(source)))
            table.setItem(row, 1, _cell(symbol))
            table.setItem(row, 2, _cell(str(target)))
        table.horizontalHeader().setStretchLastSection(True)
        table.setMaximumHeight(180)
        layout.addWidget(table)
        self._draw(service)

    def _draw(self, service: AnalyzerService) -> None:
        table = service.table
        positions = {
            state: (80 + (state % 5) * 165, 70 + (state // 5) * 145)
            for state in range(len(table.states))
        }
        for (source, symbol), target in sorted(table.transitions.items()):
            x1, y1 = positions[source]
            x2, y2 = positions[target]
            line = QGraphicsLineItem(x1, y1, x2, y2)
            line.setPen(QPen(QColor("#718096"), 1.4))
            self.scene.addItem(line)
            label = QGraphicsTextItem(symbol)
            label.setDefaultTextColor(QColor("#2255a4"))
            label.setPos((x1 + x2) / 2, (y1 + y2) / 2)
            self.scene.addItem(label)
        for state, (x, y) in positions.items():
            node = QGraphicsEllipseItem(x - 31, y - 22, 62, 44)
            node.setBrush(QBrush(QColor("#eaf1ff")))
            node.setPen(QPen(QColor("#4263a5"), 2))
            self.scene.addItem(node)
            label = QGraphicsTextItem(f"I{state}")
            label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            label.setPos(x - 11, y - 12)
            self.scene.addItem(label)
        width = 80 + 4 * 165 + 100
        height = 70 + ((len(table.states) - 1) // 5) * 145 + 90
        self.scene.setSceneRect(0, 0, width, height)


class TableView(QWidget):
    def __init__(self, service: AnalyzerService):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(_title("Tabla ACTION / GOTO"))
        table_data = service.table
        terminals = sorted(table_data.grammar.terminals)
        nonterminals = sorted(table_data.grammar.nonterminals - {table_data.grammar.start_symbol})
        table = QTableWidget(len(table_data.states), 1 + len(terminals) + len(nonterminals))
        table.setHorizontalHeaderLabels(["Estado"] + terminals + nonterminals)
        for state in range(len(table_data.states)):
            table.setItem(state, 0, _cell(str(state)))
            for column, symbol in enumerate(terminals, start=1):
                action = table_data.action.get((state, symbol))
                if action:
                    table.setItem(state, column, _cell(str(action)))
            for offset, symbol in enumerate(nonterminals, start=1 + len(terminals)):
                target = table_data.goto.get((state, symbol))
                if target is not None:
                    table.setItem(state, offset, _cell(str(target)))
        table.horizontalHeader().setStretchLastSection(True)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(table)
        layout.addWidget(
            QLabel("sN = SHIFT al estado N; rN = REDUCE usando la producción N.")
        )


class SimulationView(QWidget):
    def __init__(self, service: AnalyzerService):
        super().__init__()
        self.service = service
        self.steps: list[TraceStep] = []
        self.position = 0
        layout = QVBoxLayout(self)
        layout.addWidget(_title("Simulación paso a paso"))
        self.input_label = QLabel("Analiza una entrada para cargar la traza.")
        layout.addWidget(self.input_label)
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            ["Paso", "Pila estados", "Pila símbolos", "Entrada restante", "Acción / regla", "Explicación"]
        )
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)
        buttons = QHBoxLayout()
        self.previous = QPushButton("← Anterior")
        self.next = QPushButton("Siguiente →")
        self.run_button = QPushButton("Ejecutar")
        self.reset = QPushButton("Reiniciar")
        self.previous.clicked.connect(lambda: self._move(-1))
        self.next.clicked.connect(lambda: self._move(1))
        self.run_button.clicked.connect(self._run)
        self.reset.clicked.connect(self._reset)
        for button in (self.previous, self.next, self.run_button, self.reset):
            buttons.addWidget(button)
        layout.addLayout(buttons)
        self._render()

    def set_analysis(self, analysis: Analysis | None) -> None:
        self.steps = analysis.parse_result.trace if analysis else []
        self.position = 0
        self.input_label.setText(
            f"Entrada: {analysis.source}" if analysis else "La entrada anterior no fue aceptada."
        )
        self._render()

    def _move(self, amount: int) -> None:
        self.position = max(0, min(len(self.steps), self.position + amount))
        self._render()

    def _run(self) -> None:
        self.position = len(self.steps)
        self._render()

    def _reset(self) -> None:
        self.position = 0
        self._render()

    def _render(self) -> None:
        visible = self.steps[: self.position]
        self.table.setRowCount(len(visible))
        for row, step in enumerate(visible):
            action = str(step.action) if step.action else ""
            production = f" — {step.production}" if step.production else ""
            values = (
                str(step.number),
                " ".join(map(str, step.states)),
                " ".join(step.symbols),
                " ".join(step.remaining_input),
                action + production,
                step.explanation,
            )
            for column, value in enumerate(values):
                self.table.setItem(row, column, _cell(value))
        if visible:
            self.table.scrollToBottom()
        self.previous.setEnabled(self.position > 0)
        self.next.setEnabled(self.position < len(self.steps))
        self.run_button.setEnabled(self.position < len(self.steps))


class SyntaxTreeView(QWidget):
    def __init__(self, service: AnalyzerService):
        super().__init__()
        self.service = service
        layout = QVBoxLayout(self)
        layout.addWidget(_title("Árbol sintáctico"))
        layout.addWidget(QLabel("Estructura generada por las reducciones del parser."))
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Nodo", "Lexema"])
        layout.addWidget(self.tree)
        self.result = QLabel("Acepta una entrada para construir su árbol.")
        layout.addWidget(self.result)

    def set_analysis(self, analysis: Analysis | None) -> None:
        self.tree.clear()
        if analysis is None or analysis.parse_result.root is None:
            self.result.setText("No hay árbol: la entrada fue rechazada.")
            return

        def append(parent: QTreeWidgetItem | None, node) -> None:
            label = node.symbol
            item = QTreeWidgetItem([label, node.value or ""])
            if parent is None:
                self.tree.addTopLevelItem(item)
            else:
                parent.addChild(item)
            for child in node.children:
                append(item, child)

        append(None, analysis.parse_result.root)
        self.tree.expandAll()
        self.result.setText("AST aceptado; evaluación calculada exclusivamente desde el árbol.")


class TestBankView(QWidget):
    VALID = [
        "1", "x", "2.5", "(3)", "1+2", "7-4", "3*8", "9/3",
        "a=5", "x=1+2", "2+3*4", "(2+3)*4", "8/4/2", "1-2-3",
        "var = 5.0 + 7.0 * (3.0 + 8.0 / 4.0)",
    ]
    INVALID = [
        "", "+1", "1+", "*2", "a=", "=2", "1 2", "(1+2", "1+2)",
        "a==2", "1*/2", "()", "1..2", "@", "x=1=2",
    ]

    def __init__(self, service: AnalyzerService):
        super().__init__()
        self.service = service
        layout = QVBoxLayout(self)
        layout.addWidget(_title("Banco de pruebas"))
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Cadena", "Esperado", "Resultado"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)
        button = QPushButton("Ejecutar 30 casos")
        button.clicked.connect(self.run_cases)
        layout.addWidget(button, alignment=Qt.AlignmentFlag.AlignLeft)
        self.summary = QLabel("Los casos se ejecutan contra el mismo lexer y parser de la aplicación.")
        layout.addWidget(self.summary)
        self.run_cases()

    def run_cases(self) -> None:
        cases = [(text, True) for text in self.VALID] + [
            (text, False) for text in self.INVALID
        ]
        self.table.setRowCount(len(cases))
        passed = 0
        for row, (source, expected) in enumerate(cases):
            try:
                self.service.analyze(source)
                accepted = True
                message = "Aceptada"
            except (LexerError, ParseError, EvaluationError, ZeroDivisionError) as error:
                accepted = False
                message = str(error)
            success = accepted == expected
            passed += int(success)
            values = (source or "(vacía)", "Válida" if expected else "Inválida",
                      "✅ " + ("correcto" if success else "falló") + f" — {message}")
            for column, value in enumerate(values):
                self.table.setItem(row, column, _cell(value))
        self.summary.setText(f"{passed} de {len(cases)} casos con resultado esperado.")


def _title(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("pageTitle")
    return label


def _cell(text: str) -> QTableWidgetItem:
    item = QTableWidgetItem(text)
    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
    return item
