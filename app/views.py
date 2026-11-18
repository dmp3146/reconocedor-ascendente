from collections import defaultdict, deque
from dataclasses import dataclass
from math import atan2, cos, hypot, sin
from time import perf_counter

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QFontMetricsF,
    QPainter,
    QPainterPath,
    QPen,
    QPolygonF,
)
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsEllipseItem,
    QGraphicsLineItem,
    QGraphicsPathItem,
    QGraphicsPolygonItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsSimpleTextItem,
    QGraphicsView,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from lexer.lexer import LexerError
from parsers.ascending.parser import ASTNode, ParseError, TraceStep
from parsers.ascending.slr import LRItem
from services.analyzer_service import Analysis, AnalysisStages, AnalyzerService, StageStatus


class Panel(QFrame):
    def __init__(self, title: str | None = None, subtitle: str | None = None):
        super().__init__()
        self.setObjectName("panel")
        self.content = QVBoxLayout(self)
        self.content.setContentsMargins(22, 20, 22, 22)
        self.content.setSpacing(14)
        if title:
            heading = QLabel(title)
            heading.setObjectName("panelTitle")
            self.content.addWidget(heading)
        if subtitle:
            description = QLabel(subtitle)
            description.setObjectName("muted")
            description.setWordWrap(True)
            self.content.addWidget(description)


class PageHeader(QWidget):
    def __init__(self, title: str, subtitle: str):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 4)
        layout.setSpacing(4)
        title_label = QLabel(title)
        title_label.setObjectName("pageTitle")
        subtitle_label = QLabel(subtitle)
        subtitle_label.setObjectName("muted")
        subtitle_label.setWordWrap(True)
        layout.addWidget(title_label)
        layout.addWidget(subtitle_label)


class MetricCard(QFrame):
    def __init__(self, title: str, value: str = "—", object_name: str = ""):
        super().__init__()
        self.setObjectName("metricCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 13, 16, 13)
        layout.setSpacing(5)
        self.title = QLabel(title.upper())
        self.title.setObjectName("metricTitle")
        self.value = QLabel(value)
        self.value.setObjectName("metricValue")
        if object_name:
            self.value.setObjectName(object_name)
        layout.addWidget(self.title)
        layout.addWidget(self.value)

    def set_value(self, value: str) -> None:
        self.value.setText(value)


class ZoomableGraphicsView(QGraphicsView):
    def __init__(self, scene: QGraphicsScene):
        super().__init__(scene)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setMinimumHeight(480)
        self.setObjectName("graphicsCanvas")

    def wheelEvent(self, event) -> None:
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        self.scale(factor, factor)

    def zoom(self, factor: float) -> None:
        self.scale(factor, factor)

    def fit_scene(self) -> None:
        bounds = self.scene().itemsBoundingRect()
        if not bounds.isEmpty():
            self.fitInView(bounds.adjusted(-50, -50, 50, 50), Qt.AspectRatioMode.KeepAspectRatio)

    def center_scene(self) -> None:
        self.centerOn(self.scene().sceneRect().center())


def _graph_controls(graph: ZoomableGraphicsView, fit_callback=None) -> QHBoxLayout:
    controls = QHBoxLayout()
    controls.setSpacing(8)
    for label, action in (
        ("−", lambda: graph.zoom(1 / 1.2)),
        ("+", lambda: graph.zoom(1.2)),
        ("Ajustar", fit_callback or graph.fit_scene),
        ("Centrar", graph.center_scene),
    ):
        button = QPushButton(label)
        button.setObjectName("secondaryButton")
        button.clicked.connect(action)
        controls.addWidget(button)
    controls.addStretch(1)
    return controls


class RecognizerView(QWidget):
    EXAMPLE = "var = 5.0 + 7.0 * (3.0 + 8.0 / 4.0)"
    TREE_EXAMPLE = "resultado = ((10 + 20) / 5) * ((8 - 3) + 1)"

    def __init__(self, service: AnalyzerService, on_analysis):
        super().__init__()
        self.service = service
        self.on_analysis = on_analysis
        self._last_source = self.EXAMPLE
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 30)
        layout.setSpacing(20)
        layout.addWidget(
            PageHeader(
                "Reconocedor Ascendente SLR(1)",
                "Escribe una expresión aritmética o asignación y observa su análisis ascendente, "
                "el árbol construido por reducciones y el resultado.",
            )
        )

        self.engine_status = QLabel(
            f"● Motor SLR(1) activo  ·  {len(service.table.states)} estados  ·  "
            f"{len(service.table.action)} acciones generadas"
        )
        self.engine_status.setObjectName("engineStatus")
        layout.addWidget(self.engine_status, alignment=Qt.AlignmentFlag.AlignLeft)

        input_panel = Panel("Entrada", "Admite identificadores, enteros, decimales, paréntesis y + − × ÷.")
        self.source = QPlainTextEdit()
        self.source.setObjectName("sourceEditor")
        self.source.setPlaceholderText("Escribe aquí la expresión...")
        self.source.setPlainText(self.EXAMPLE)
        self.source.setMinimumHeight(125)
        self.source.setMaximumHeight(175)
        input_panel.content.addWidget(self.source)
        buttons = QHBoxLayout()
        self.analyze_button = QPushButton("Analizar")
        self.analyze_button.setObjectName("primaryButton")
        self.analyze_button.clicked.connect(self.analyze)
        clear_button = QPushButton("Limpiar")
        clear_button.setObjectName("secondaryButton")
        clear_button.clicked.connect(self.clear)
        example_button = QPushButton("Cargar ejemplo · 40.0")
        example_button.setObjectName("secondaryButton")
        example_button.clicked.connect(lambda: self.load_example(self.EXAMPLE))
        tree_example_button = QPushButton("Ejemplo para el AST")
        tree_example_button.setObjectName("secondaryButton")
        tree_example_button.clicked.connect(lambda: self.load_example(self.TREE_EXAMPLE))
        for button in (self.analyze_button, clear_button, example_button, tree_example_button):
            buttons.addWidget(button)
        buttons.addStretch(1)
        input_panel.content.addLayout(buttons)
        layout.addWidget(input_panel)

        self.result_panel = Panel("Resultado del análisis")
        self.result_panel.setObjectName("resultPanel")
        self.result_panel.setProperty("status", "idle")
        self.result_status = QLabel("LISTO PARA ANALIZAR")
        self.result_status.setObjectName("resultStatus")
        self.result_value = QLabel("—")
        self.result_value.setObjectName("resultValue")
        self.result_value.setMinimumHeight(66)
        self.result_expression = QLabel("Carga un ejemplo o introduce una expresión.")
        self.result_expression.setObjectName("resultExpression")
        self.result_expression.setWordWrap(True)
        self.result_message = QLabel(
            "El parser SLR(1) generará la traza y el AST desde las reducciones reales."
        )
        self.result_message.setObjectName("resultMessage")
        self.result_message.setWordWrap(True)
        self.result_panel.content.addWidget(self.result_status)
        self.result_panel.content.addWidget(self.result_value)
        self.result_panel.content.addWidget(self.result_expression)
        self.result_panel.content.addWidget(self.result_message)
        self.stage_summary = QLabel()
        self.stage_summary.setObjectName("symbolSummary")
        self.stage_summary.setWordWrap(True)
        self.result_panel.content.addWidget(self.stage_summary)
        metrics = QHBoxLayout()
        metrics.setSpacing(12)
        self.time_metric = MetricCard("Tiempo", "—")
        self.tokens_metric = MetricCard("Tokens", "—")
        self.steps_metric = MetricCard("Pasos", "—")
        self.final_metric = MetricCard("Estado del parser", "—")
        for metric in (self.time_metric, self.tokens_metric, self.steps_metric, self.final_metric):
            metrics.addWidget(metric, 1)
        self.result_panel.content.addLayout(metrics)
        self.tokens = QLabel()
        self.tokens.setObjectName("tokenLine")
        self.tokens.setWordWrap(True)
        self.result_panel.content.addWidget(self.tokens)
        layout.addWidget(self.result_panel)
        layout.addStretch(1)
        self.stage_summary.setText("Análisis por etapas: pendiente.")

    def load_example(self, source: str) -> None:
        self.source.setPlainText(source)
        self.source.setFocus()

    def clear(self) -> None:
        self.source.clear()
        self._last_source = ""
        self._set_status("idle")
        self.result_status.setText("LISTO PARA ANALIZAR")
        self.result_value.setText("—")
        self.result_expression.setText("Introduce una expresión para comenzar.")
        self.result_message.setText("")
        self.stage_summary.setText("Análisis por etapas: pendiente.")
        self.tokens.setText("")
        for metric in (self.time_metric, self.tokens_metric, self.steps_metric, self.final_metric):
            metric.set_value("—")
        self.on_analysis(None, None, "")

    def analyze(self) -> None:
        source = self.source.toPlainText()
        self._last_source = source
        started = perf_counter()
        stages = self.service.analyze_stages(source)
        elapsed_ms = (perf_counter() - started) * 1000
        self._show_stages(stages)
        analysis = stages.analysis
        if analysis is None:
            if stages.error is None:
                raise RuntimeError("El análisis falló sin proporcionar un error")
            self._show_rejection(source, stages.error, elapsed_ms)
            self.on_analysis(None, stages.error, source)
            return

        if stages.evaluation == StageStatus.ERROR:
            self._set_status("evaluationError")
            self.result_status.setText("ERROR DE EVALUACIÓN")
            self.result_value.setText("NO EVALUABLE")
            if analysis.division_by_zero:
                self.result_message.setText(
                    "Error semántico: división entre cero. La expresión es sintácticamente "
                    "válida, pero no tiene un resultado numérico definido."
                )
            else:
                self.result_message.setText(
                    f"Error semántico: {analysis.evaluation_error}. "
                    "La expresión es sintácticamente válida, pero no puede evaluarse."
                )
        else:
            self._set_status("accepted")
            self.result_status.setText("CADENA ACEPTADA")
            self.result_value.setText(
                f"{analysis.variable} = {analysis.value}" if analysis.variable else str(analysis.value)
            )
            self.result_message.setText(
                "La cadena pertenece a la gramática y el valor se calculó recorriendo el AST."
            )
        self.result_expression.setText(f"Expresión:  {source}")
        self.time_metric.set_value(f"{elapsed_ms:.2f} ms")
        self.tokens_metric.set_value(str(max(0, len(analysis.tokens) - 1)))
        self.steps_metric.set_value(str(len(analysis.parse_result.trace)))
        final_action = analysis.parse_result.trace[-1].action if analysis.parse_result.trace else None
        self.final_metric.set_value(str(final_action).upper() if final_action else "—")
        self.tokens.setText("TOKENS   " + "   ·   ".join(token.symbol for token in analysis.tokens[:-1]))
        self.on_analysis(analysis, None, source)

    def _show_stages(self, stages: AnalysisStages) -> None:
        tree_status = (
            "GENERADO" if stages.analysis is not None
            and stages.analysis.parse_result.root is not None else "NO GENERADO"
        )
        final_status = (
            "NO EVALUABLE" if stages.evaluation == StageStatus.ERROR
            else "RESULTADO DISPONIBLE" if stages.evaluation == StageStatus.CORRECT
            else "NO DISPONIBLE"
        )
        self.stage_summary.setText(
            f"Análisis léxico: {stages.lexical.value}  ·  "
            f"Análisis sintáctico: {stages.syntactic.value}  ·  "
            f"Árbol sintáctico: {tree_status}\n"
            f"Evaluación: {stages.evaluation.value}  ·  Resultado final: {final_status}"
        )

    def _show_rejection(self, source: str, error: Exception, elapsed_ms: float) -> None:
        self._set_status("rejected")
        self.result_status.setText("CADENA RECHAZADA")
        self.result_value.setText("Entrada no válida")
        self.result_expression.setText(f"Expresión:  {source or '(vacía)'}")
        self.result_message.setText(str(error))
        self.tokens.setText("")
        self.time_metric.set_value(f"{elapsed_ms:.2f} ms")
        self.tokens_metric.set_value("—")
        trace = error.trace if isinstance(error, ParseError) else []
        self.steps_metric.set_value(str(len(trace) + 1) if isinstance(error, ParseError) else "0")
        self.final_metric.set_value("ERROR" if isinstance(error, ParseError) else "NO EJECUTADO")

    def _set_status(self, status: str) -> None:
        self.result_panel.setProperty("status", status)
        self.result_panel.style().unpolish(self.result_panel)
        self.result_panel.style().polish(self.result_panel)


class GrammarView(QWidget):
    def __init__(self, service: AnalyzerService):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 30)
        layout.setSpacing(20)
        grammar = service.table.grammar
        layout.addWidget(
            PageHeader(
                "Gramática y conjuntos",
                "La gramática aumentada es la fuente de las producciones, los conjuntos FIRST/FOLLOW "
                "y la tabla SLR(1).",
            )
        )
        summary = QHBoxLayout()
        summary.setSpacing(12)
        summary.addWidget(MetricCard("Símbolo inicial", grammar.start_symbol))
        summary.addWidget(MetricCard("Producciones", str(len(grammar.productions))))
        summary.addWidget(MetricCard("Terminales", str(len(grammar.terminals))))
        summary.addWidget(MetricCard("No terminales", str(len(grammar.nonterminals))))
        layout.addLayout(summary)
        layout.addWidget(
            QLabel("Terminales:  " + "   ·   ".join(sorted(grammar.terminals)),
                   objectName="symbolSummary")
        )
        layout.addWidget(
            QLabel("No terminales:  " + "   ·   ".join(sorted(grammar.nonterminals)),
                   objectName="symbolSummary")
        )
        production_panel = Panel(
            "Producciones",
            "P₀ es la producción aumentada; los niveles E, T y F expresan precedencia y asociatividad.",
        )
        productions = QTableWidget(len(grammar.productions), 3)
        productions.setHorizontalHeaderLabels(["Producción", "Regla", "FOLLOW del lado izquierdo"])
        productions.setColumnWidth(0, 115)
        productions.setColumnWidth(1, 330)
        productions.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        for row, production in enumerate(grammar.productions):
            follow = service.table.follow.get(production.lhs, set())
            productions.setItem(row, 0, _cell(f"P{production.index}"))
            productions.setItem(row, 1, _cell(str(production)))
            productions.setItem(row, 2, _cell(",  ".join(sorted(follow)) or "—"))
            productions.setRowHeight(row, 42)
        _prepare_table(productions)
        production_panel.content.addWidget(productions)
        layout.addWidget(production_panel)

        sets_row = QHBoxLayout()
        sets_row.setSpacing(16)
        first_panel = Panel("FIRST")
        follow_panel = Panel("FOLLOW")
        first_table = QTableWidget(len(grammar.nonterminals), 2)
        first_table.setHorizontalHeaderLabels(["No terminal", "Conjunto FIRST"])
        follow_table = QTableWidget(len(grammar.nonterminals), 2)
        follow_table.setHorizontalHeaderLabels(["No terminal", "Conjunto FOLLOW"])
        first_sets = grammar.first_sets()
        for row, symbol in enumerate(sorted(grammar.nonterminals)):
            first_table.setItem(row, 0, _cell(symbol))
            first_table.setItem(row, 1, _cell(" { " + ", ".join(sorted(first_sets[symbol])) + " }"))
            follow_table.setItem(row, 0, _cell(symbol))
            follow_table.setItem(
                row, 1, _cell(" { " + ", ".join(sorted(service.table.follow[symbol])) + " }")
            )
            first_table.setRowHeight(row, 40)
            follow_table.setRowHeight(row, 40)
        for table in (first_table, follow_table):
            table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
            _prepare_table(table)
        first_panel.content.addWidget(first_table)
        follow_panel.content.addWidget(follow_table)
        sets_row.addWidget(first_panel, 1)
        sets_row.addWidget(follow_panel, 1)
        layout.addLayout(sets_row)


class StateNodeItem(QGraphicsEllipseItem):
    def __init__(self, state: int, rect: QRectF, accepted: bool, on_selected):
        super().__init__(rect)
        self.state = state
        self._on_selected = on_selected
        self.setFlag(QGraphicsEllipseItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setBrush(QBrush(QColor("#fff3cd" if accepted else "#e8f0ff")))
        self.setPen(QPen(QColor("#d49a20" if accepted else "#4266a1"), 3 if accepted else 2))
        self.setZValue(2)

    def mousePressEvent(self, event) -> None:
        super().mousePressEvent(event)
        self._on_selected(self.state)


@dataclass(frozen=True)
class AutomatonStep:
    action: str
    origin: int
    lookahead: str
    destination: int | None
    transition_origin: int | None
    transition_symbol: str | None
    explanation: str


class AutomatonView(QWidget):
    def __init__(self, service: AnalyzerService):
        super().__init__()
        self.table_data = service.table
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 30)
        layout.setSpacing(18)
        layout.addWidget(
            PageHeader(
                "Autómata canónico LR(0)",
                "Estados, ítems LR(0) y transiciones obtenidos con CLOSURE/GOTO por el generador SLR(1). "
                "Selecciona un estado para inspeccionar sus ítems.",
            )
        )
        panel = Panel("Estados y transiciones")
        self.scene = QGraphicsScene(self)
        self.graph = ZoomableGraphicsView(self.scene)
        panel.content.addLayout(_graph_controls(self.graph))
        route_controls = QHBoxLayout()
        self.full_route_button = QPushButton("Ver recorrido completo")
        self.previous_step_button = QPushButton("← Retroceder")
        self.next_step_button = QPushButton("Avanzar →")
        self.reset_route_button = QPushButton("Reiniciar recorrido")
        self.show_automaton_button = QPushButton("Mostrar autómata completo")
        for button in (
            self.full_route_button, self.previous_step_button, self.next_step_button,
            self.reset_route_button, self.show_automaton_button,
        ):
            button.setObjectName("secondaryButton")
            route_controls.addWidget(button)
        route_controls.addStretch(1)
        panel.content.addLayout(route_controls)
        self.route_context = QLabel("Analiza una expresión para visualizar su recorrido.")
        self.route_context.setWordWrap(True)
        self.route_context.setObjectName("simulationInput")
        panel.content.addWidget(self.route_context)
        self.graph.setMinimumHeight(530)
        panel.content.addWidget(self.graph, 1)
        legend = QLabel(
            "I0 · inicio     ● Azul · no visitado     ● Dorado · ACCEPT     "
            "● Verde · visitado     ● Naranja · actual"
        )
        legend.setObjectName("muted")
        panel.content.addWidget(legend)
        layout.addWidget(panel, 1)
        self.detail_panel = Panel("Detalle del estado I0", "Ítems del conjunto LR(0) seleccionado.")
        self.detail = QPlainTextEdit()
        self.detail.setObjectName("stateDetails")
        self.detail.setReadOnly(True)
        self.detail.setMinimumHeight(150)
        self.detail_panel.content.addWidget(self.detail)
        layout.addWidget(self.detail_panel)
        self.state_items: dict[int, StateNodeItem] = {}
        self.edge_items: dict[tuple[int, int], tuple[QGraphicsPathItem, QGraphicsPolygonItem]] = {}
        self.route_steps: list[AutomatonStep] = []
        self.route_position = 0
        self.route_source = ""
        self.route_message = ""
        self.showing_route = False
        self.selected_state = 0
        self.full_route_button.clicked.connect(self._show_full_route)
        self.previous_step_button.clicked.connect(lambda: self._move_route(-1))
        self.next_step_button.clicked.connect(lambda: self._move_route(1))
        self.reset_route_button.clicked.connect(self._reset_route)
        self.show_automaton_button.clicked.connect(self._show_full_automaton)
        self._draw()
        self.select_state(0)
        self._render_route()

    def _draw(self) -> None:
        table = self.table_data
        distances = {0: 0}
        pending = deque([0])
        while pending:
            state = pending.popleft()
            for (origin, _), target in table.transitions.items():
                if origin == state and target not in distances:
                    distances[target] = distances[state] + 1
                    pending.append(target)
        layers: dict[int, list[int]] = defaultdict(list)
        for state in range(len(table.states)):
            layers[distances.get(state, 0)].append(state)

        positions: dict[int, tuple[float, float]] = {}
        for layer, states in layers.items():
            for row, state in enumerate(sorted(states)):
                positions[state] = (
                    115 + layer * 245,
                    105 + row * 150,
                )

        grouped_edges: dict[tuple[int, int], list[str]] = defaultdict(list)
        for (origin, symbol), target in table.transitions.items():
            grouped_edges[(origin, target)].append(symbol)
        for (origin, target), symbols in sorted(grouped_edges.items()):
            x1, y1 = positions[origin]
            x2, y2 = positions[target]
            color = QColor("#71839d")
            if origin == target:
                path = QPainterPath(QPointF(x1 + 27, y1 - 31))
                path.cubicTo(x1 + 74, y1 - 94, x1 - 74, y1 - 94, x1 - 27, y1 - 31)
                tangent = QPointF(x1 - 22, y1 - 42)
                end = QPointF(x1 - 27, y1 - 31)
            else:
                dx, dy = x2 - x1, y2 - y1
                length = max(hypot(dx, dy), 1)
                ux, uy = dx / length, dy / length
                start = QPointF(x1 + ux * 44, y1 + uy * 44)
                end = QPointF(x2 - ux * 47, y2 - uy * 47)
                path = QPainterPath(start)
                path.lineTo(end)
                tangent = QPointF(end.x() - ux * 12, end.y() - uy * 12)
            edge = QGraphicsPathItem(path)
            edge.setPen(QPen(color, 1.8))
            edge.setZValue(0)
            self.scene.addItem(edge)
            dx, dy = end.x() - tangent.x(), end.y() - tangent.y()
            angle = atan2(dy, dx)
            size = 10
            base = QPointF(end.x() - size * cos(angle), end.y() - size * sin(angle))
            arrow = QPolygonF(
                [
                    end,
                    QPointF(base.x() + 5 * sin(angle), base.y() - 5 * cos(angle)),
                    QPointF(base.x() - 5 * sin(angle), base.y() + 5 * cos(angle)),
                ]
            )
            arrow_item = QGraphicsPolygonItem(arrow)
            arrow_item.setBrush(QBrush(color))
            arrow_item.setPen(QPen(color))
            arrow_item.setZValue(1)
            self.scene.addItem(arrow_item)
            self.edge_items[(origin, target)] = (edge, arrow_item)
            edge_label = QGraphicsSimpleTextItem(", ".join(sorted(symbols)))
            edge_label.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
            edge_label.setBrush(QBrush(QColor("#234a83")))
            edge_label.setPos((x1 + x2) / 2 - 20, (y1 + y2) / 2 - 22)
            edge_label.setZValue(3)
            self.scene.addItem(edge_label)

        for state, (x, y) in positions.items():
            is_accept = LRItem(0, 1) in table.states[state]
            node = StateNodeItem(
                state,
                QRectF(x - 43, y - 43, 86, 86),
                is_accept,
                self.select_state,
            )
            self.scene.addItem(node)
            self.state_items[state] = node
            label = QGraphicsSimpleTextItem(f"I{state}")
            label.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
            label.setBrush(QBrush(QColor("#17345c")))
            label.setPos(x - label.boundingRect().width() / 2, y - label.boundingRect().height() / 2)
            label.setZValue(4)
            self.scene.addItem(label)
        self.scene.setSceneRect(self.scene.itemsBoundingRect().adjusted(-70, -100, 70, 70))

    def select_state(self, state: int) -> None:
        self.selected_state = state
        for number, item in self.state_items.items():
            item.setSelected(number == state)
        self._style_route()
        items = self.table_data.state_items(state)
        self.detail_panel.findChild(QLabel, "panelTitle").setText(f"Detalle del estado I{state}")
        self.detail.setPlainText("\n".join(f"  {item}" for item in items))

    def set_analysis(
        self, analysis: Analysis | None, error: Exception | None, source: str
    ) -> None:
        self.route_source = source
        self.route_steps = []
        self.route_position = 0
        self.route_message = ""
        self.showing_route = False
        if analysis is not None:
            trace = analysis.parse_result.trace
        elif isinstance(error, ParseError):
            trace = error.trace
        else:
            trace = []
            if isinstance(error, LexerError):
                self.route_message = f"Error léxico; el parser no se ejecutó: {error}"
            elif error is not None:
                self.route_message = str(error)

        current_state = 0
        for step in trace:
            if step.action is None:
                raise RuntimeError("La traza contiene una acción ausente")
            origin = step.states[-1]
            lookahead = step.remaining_input[0]
            kind = step.action.kind
            destination = None
            transition_origin = None
            transition_symbol = None
            if kind == "shift":
                transition_origin = origin
                transition_symbol = lookahead
                destination = step.action.value
            elif kind == "reduce":
                if step.production is None:
                    raise RuntimeError("La reducción no indica una producción")
                count = len(step.production.rhs)
                transition_origin = step.states[-count - 1]
                transition_symbol = step.production.lhs
                destination = self.table_data.goto.get((transition_origin, transition_symbol))
            elif kind != "accept":
                raise RuntimeError(f"Acción inesperada en la traza: {kind}")
            if transition_origin is not None:
                actual = self.table_data.transitions.get((transition_origin, transition_symbol))
                if destination is None or actual != destination:
                    raise RuntimeError("La traza no coincide con las transiciones del autómata")
                current_state = destination
            else:
                current_state = origin
            self.route_steps.append(
                AutomatonStep(
                    kind.upper(), origin, lookahead, destination,
                    transition_origin, transition_symbol, step.explanation,
                )
            )
        if isinstance(error, ParseError):
            self.route_steps.append(
                AutomatonStep("ERROR", current_state, error.token.symbol, None, None, None, str(error))
            )
        self.showing_route = bool(self.route_steps)
        self._render_route()

    def _move_route(self, amount: int) -> None:
        self.showing_route = True
        self.route_position = max(0, min(len(self.route_steps), self.route_position + amount))
        self._render_route()

    def _show_full_route(self) -> None:
        self.showing_route = True
        self.route_position = len(self.route_steps)
        self._render_route()

    def _reset_route(self) -> None:
        self.showing_route = bool(self.route_steps)
        self.route_position = 0
        self._render_route()

    def _show_full_automaton(self) -> None:
        self.showing_route = False
        self._render_route()
        self.graph.fit_scene()

    def _render_route(self) -> None:
        total = len(self.route_steps)
        if not total:
            self.route_context.setText(
                self.route_message or "Analiza una expresión para visualizar su recorrido."
            )
        elif not self.showing_route:
            self.route_context.setText(
                f"Expresión: {self.route_source}  ·  Autómata completo sin resaltado. "
                f"Recorrido conservado: paso {self.route_position} de {total}."
            )
        elif self.route_position == 0:
            self.route_context.setText(
                f"Expresión: {self.route_source}  ·  Paso 0 de {total}  ·  Estado inicial I0"
            )
        else:
            step = self.route_steps[self.route_position - 1]
            transition = (
                f"I{step.transition_origin} — {step.transition_symbol} → I{step.destination}"
                if step.transition_origin is not None else "sin transición"
            )
            symbol_label = (
                "Símbolo leído" if step.action == "SHIFT" else "Símbolo pendiente (no consumido)"
            )
            self.route_context.setText(
                f"Expresión: {self.route_source}  ·  Paso {self.route_position} de {total}\n"
                f"Acción: {step.action}  ·  Estado de acción: I{step.origin}  ·  "
                f"{symbol_label}: {step.lookahead}  ·  Transición: {transition}\n"
                f"{step.explanation}"
            )
        self.previous_step_button.setEnabled(total > 0 and self.route_position > 0)
        self.next_step_button.setEnabled(total > 0 and self.route_position < total)
        self.full_route_button.setEnabled(total > 0)
        self.reset_route_button.setEnabled(total > 0)
        self._style_route()

    def _style_route(self) -> None:
        visited: set[int] = set()
        traversed_edges: set[tuple[int, int]] = set()
        current = None
        current_edge = None
        if self.showing_route and self.route_steps:
            visited.add(0)
            current = 0
            for step in self.route_steps[:self.route_position]:
                visited.add(step.origin)
                current = step.origin
                if step.transition_origin is not None and step.destination is not None:
                    visited.update((step.transition_origin, step.destination))
                    current = step.destination
                    current_edge = (step.transition_origin, step.destination)
                    traversed_edges.add(current_edge)
                else:
                    current_edge = None
        for state, item in self.state_items.items():
            accepted = LRItem(0, 1) in self.table_data.states[state]
            if state == current:
                fill, border = "#ffe2b5", "#d56b09"
            elif state in visited:
                fill, border = "#d9f3e5", "#16814b"
            else:
                fill = "#fff3cd" if accepted else "#e8f0ff"
                border = "#d49a20" if accepted else "#4266a1"
            item.setBrush(QBrush(QColor(fill)))
            item.setPen(QPen(QColor(border), 4 if state == self.selected_state else 2.5))
        for edge_key, (edge, arrow) in self.edge_items.items():
            color = QColor(
                "#d56b09" if edge_key == current_edge else
                "#16814b" if edge_key in traversed_edges else "#71839d"
            )
            width = 4.5 if edge_key == current_edge else 3.2 if edge_key in traversed_edges else 1.8
            edge.setPen(QPen(color, width))
            arrow.setBrush(QBrush(color))
            arrow.setPen(QPen(color))


class TableView(QWidget):
    def __init__(self, service: AnalyzerService):
        super().__init__()
        self.table_data = service.table
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 30)
        layout.setSpacing(18)
        layout.addWidget(
            PageHeader(
                "Tabla ACTION / GOTO",
                "Celdas generadas a partir del autómata LR(0) y FOLLOW; los estados y acciones "
                "son los que consume el parser.",
            )
        )
        status = QLabel("● 0 conflictos · la gramática se analizó sin conflictos SLR(1)")
        status.setObjectName("successBadge")
        layout.addWidget(status, alignment=Qt.AlignmentFlag.AlignLeft)
        panel = Panel("Tabla del parser")
        terminals = sorted(service.table.grammar.terminals)
        nonterminals = sorted(
            service.table.grammar.nonterminals - {service.table.grammar.start_symbol}
        )
        action_count = len(terminals)
        columns = 1 + action_count + len(nonterminals)
        rows = len(service.table.states) + 2
        table = QTableWidget(rows, columns)
        table.setObjectName("lrTable")
        table.setHorizontalHeaderLabels([""] * columns)
        table.setVerticalHeaderLabels(["", ""] + [str(i) for i in range(len(service.table.states))])
        table.setSpan(0, 0, 2, 1)
        table.setItem(0, 0, _cell("ESTADO"))
        table.setSpan(0, 1, 1, action_count)
        table.setItem(0, 1, _cell("ACTION  ·  terminales"))
        table.setSpan(0, 1 + action_count, 1, len(nonterminals))
        table.setItem(0, 1 + action_count, _cell("GOTO  ·  no terminales"))
        for column, symbol in enumerate(terminals, start=1):
            table.setItem(1, column, _cell(symbol))
        for column, symbol in enumerate(nonterminals, start=1 + action_count):
            table.setItem(1, column, _cell(symbol))
        for state in range(len(service.table.states)):
            row = state + 2
            table.setItem(row, 0, _cell(f"I{state}"))
            for column, symbol in enumerate(terminals, start=1):
                action = service.table.action.get((state, symbol))
                if action:
                    item = _cell(str(action))
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    if action.kind == "shift":
                        item.setBackground(QBrush(QColor("#eaf3ff")))
                        item.setForeground(QBrush(QColor("#1b5fad")))
                    elif action.kind == "reduce":
                        item.setBackground(QBrush(QColor("#fff3e8")))
                        item.setForeground(QBrush(QColor("#9a4a0a")))
                    elif action.kind == "accept":
                        item.setBackground(QBrush(QColor("#e4f6ed")))
                        item.setForeground(QBrush(QColor("#11764b")))
                    table.setItem(row, column, item)
            for column, symbol in enumerate(nonterminals, start=1 + action_count):
                target = service.table.goto.get((state, symbol))
                if target is not None:
                    table.setItem(row, column, _cell(str(target)))
            table.setRowHeight(row, 43)
        table.setRowHeight(0, 38)
        table.setRowHeight(1, 42)
        table.setColumnWidth(0, 82)
        for column in range(1, columns):
            table.setColumnWidth(column, 105)
        table.setHorizontalScrollMode(QTableWidget.ScrollMode.ScrollPerPixel)
        table.setVerticalScrollMode(QTableWidget.ScrollMode.ScrollPerPixel)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setAlternatingRowColors(True)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        table.verticalHeader().setDefaultSectionSize(43)
        table.setMinimumHeight(580)
        panel.content.addWidget(table, 1)
        legend = QLabel("SHIFT · azul     REDUCE · ámbar     ACCEPT · verde     GOTO · estado destino")
        legend.setObjectName("muted")
        panel.content.addWidget(legend)
        layout.addWidget(panel, 1)
        self.table = table


class SimulationView(QWidget):
    def __init__(self, service: AnalyzerService):
        super().__init__()
        self.service = service
        self.steps: list[TraceStep] = []
        self.position = 0
        self.error_message: str | None = None
        self.source = ""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 30)
        layout.setSpacing(18)
        layout.addWidget(
            PageHeader(
                "Simulación del análisis ascendente",
                "Recorre la traza real del parser. Cada fila muestra la configuración antes de aplicar "
                "SHIFT, REDUCE, ACCEPT o ERROR.",
            )
        )
        self.input_label = QLabel("Analiza una entrada para cargar la traza.")
        self.input_label.setObjectName("simulationInput")
        layout.addWidget(self.input_label)
        controls_panel = Panel("Controles de ejecución")
        buttons = QHBoxLayout()
        self.start_button = QPushButton("Iniciar")
        self.previous = QPushButton("← Paso anterior")
        self.next = QPushButton("Siguiente paso →")
        self.run_button = QPushButton("Ejecutar hasta el final")
        self.reset = QPushButton("Reiniciar")
        for button in (self.start_button, self.previous, self.next, self.run_button, self.reset):
            button.setObjectName("secondaryButton")
            buttons.addWidget(button)
        self.start_button.clicked.connect(self._start)
        self.previous.clicked.connect(lambda: self._move(-1))
        self.next.clicked.connect(lambda: self._move(1))
        self.run_button.clicked.connect(self._run)
        self.reset.clicked.connect(self._reset)
        buttons.addStretch(1)
        controls_panel.content.addLayout(buttons)
        layout.addWidget(controls_panel)

        self.current_state = QLabel("Estado actual: —")
        self.current_state.setObjectName("stateBadge")
        self.current_action = QLabel("Inicia la simulación para avanzar.")
        self.current_action.setObjectName("actionExplanation")
        layout.addWidget(self.current_state)
        explanation = Panel("¿Qué ocurrió en este paso?")
        explanation.content.addWidget(self.current_action)
        layout.addWidget(explanation)

        panel = Panel("Traza de parsing", "La pila y la entrada corresponden a la configuración anterior a la acción.")
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            ["Paso", "Estado", "Pila de estados", "Pila de símbolos", "Entrada restante", "Acción", "Producción"]
        )
        for col, width in enumerate((62, 78, 180, 190, 220, 100, 300)):
            self.table.setColumnWidth(col, width)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setDefaultSectionSize(50)
        self.table.cellClicked.connect(self._select_row)
        panel.content.addWidget(self.table)
        layout.addWidget(panel, 1)
        self._render()

    def set_analysis(self, analysis: Analysis | None) -> None:
        self.source = analysis.source if analysis else ""
        self.steps = analysis.parse_result.trace if analysis else []
        self.error_message = None
        self.position = 0
        self.input_label.setText(
            f"ENTRADA  {self.source}"
            + ("  ·  Sintaxis aceptada; error de evaluación" if analysis.evaluation_error else "")
            if analysis
            else "Analiza una entrada para cargar la traza."
        )
        self._render()

    def set_rejection(self, source: str, error: Exception) -> None:
        self.source = source
        self.steps = error.trace if isinstance(error, ParseError) else []
        self.error_message = str(error) if isinstance(error, ParseError) else None
        self.position = 0
        self.input_label.setText(
            f"ENTRADA  {source or '(vacía)'}"
            + (f"  ·  Error léxico; parser no ejecutado: {error}" if isinstance(error, LexerError) else "")
        )
        self._render()
        if isinstance(error, LexerError):
            self.current_state.setText("PARSER NO EJECUTADO")
            self.current_action.setText(str(error))

    @property
    def total_rows(self) -> int:
        return len(self.steps) + int(self.error_message is not None)

    def _start(self) -> None:
        self.position = 1 if self.total_rows else 0
        self._render()

    def _move(self, amount: int) -> None:
        self.position = max(0, min(self.total_rows, self.position + amount))
        self._render()

    def _run(self) -> None:
        self.position = self.total_rows
        self._render()

    def _reset(self) -> None:
        self.position = 0
        self._render()

    def _select_row(self, row: int, _column: int) -> None:
        self.position = min(row + 1, self.total_rows)
        self._render()

    def _render(self) -> None:
        self.table.setRowCount(0)
        visible_count = min(self.position, self.total_rows)
        visible_steps = min(visible_count, len(self.steps))
        for row, step in enumerate(self.steps[:visible_steps]):
            action_kind = step.action.kind if step.action else ""
            production = str(step.production) if step.production else "—"
            action_label = action_kind.upper() if action_kind else "—"
            state = step.states[-1] if step.states else 0
            values = (
                str(step.number + 1),
                str(state),
                "0  " + "  ".join(map(str, step.states[1:])),
                "  ".join(step.symbols) or "—",
                "  ".join(step.remaining_input) or "$",
                action_label,
                production,
            )
            self._add_trace_row(row, values, action_kind, step.explanation)
        if visible_count > len(self.steps) and self.error_message is not None:
            row = len(self.steps)
            state = self.steps[-1].states[-1] if self.steps and self.steps[-1].states else 0
            values = (
                "ERR",
                str(state),
                "—",
                "—",
                "—",
                "ERROR",
                self.error_message,
            )
            self._add_trace_row(row, values, "error", self.error_message)

        if visible_count:
            row_index = visible_count - 1
            self.table.selectRow(row_index)
            self.table.scrollToBottom()
            if row_index < len(self.steps):
                step = self.steps[row_index]
                state = step.states[-1] if step.states else 0
                action = str(step.action).upper() if step.action else "—"
                self.current_state.setText(f"PASO {step.number + 1}  ·  ESTADO ACTUAL I{state}  ·  {action}")
                self.current_action.setText(step.explanation)
            else:
                self.current_state.setText(f"ESTADO ACTUAL I{self.steps[-1].states[-1] if self.steps else 0}  ·  ERROR")
                self.current_action.setText(self.error_message or "La entrada fue rechazada.")
        else:
            self.current_state.setText("ESTADO ACTUAL: I0  ·  INICIO")
            self.current_action.setText("Pulsa Iniciar o Siguiente paso para recorrer la traza.")
        self.start_button.setEnabled(self.position == 0 and self.total_rows > 0)
        self.previous.setEnabled(self.position > 0)
        self.next.setEnabled(self.position < self.total_rows)
        self.run_button.setEnabled(self.position < self.total_rows)
        self.reset.setEnabled(self.position > 0)

    def _add_trace_row(self, row: int, values: tuple[str, ...], kind: str, explanation: str) -> None:
        self.table.insertRow(row)
        colors = {
            "shift": QColor("#eaf3ff"),
            "reduce": QColor("#fff3e8"),
            "accept": QColor("#e4f6ed"),
            "error": QColor("#fde9e7"),
        }
        foregrounds = {
            "shift": QColor("#1b5fad"),
            "reduce": QColor("#9a4a0a"),
            "accept": QColor("#11764b"),
            "error": QColor("#b42318"),
        }
        for column, value in enumerate(values):
            item = _cell(value)
            item.setToolTip(explanation)
            if column == 5 and kind in colors:
                item.setBackground(QBrush(colors[kind]))
                item.setForeground(QBrush(foregrounds[kind]))
                font = item.font()
                font.setBold(True)
                item.setFont(font)
            self.table.setItem(row, column, item)
        self.table.setRowHeight(row, 54)


class SyntaxTreeView(QWidget):
    _palette = {
        "grammar": ("#eaf1ff", "#31598f"),
        "operator": ("#f0eafe", "#7952a4"),
        "operand": ("#e5f6ed", "#288258"),
        "punctuation": ("#f0f3f7", "#8592a5"),
    }

    def __init__(self, service: AnalyzerService):
        super().__init__()
        self.service = service
        self.ast_node_items: dict[int, QGraphicsRectItem] = {}
        self.ast_root: ASTNode | None = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 30)
        layout.setSpacing(18)
        layout.addWidget(
            PageHeader(
                "Árbol sintáctico (AST)",
                "Cada nodo corresponde a un nodo del AST construido por el parser durante REDUCE. "
                "Arrastra para desplazarte y usa la rueda o los controles para cambiar el zoom.",
            )
        )
        panel = Panel("Estructura derivada de la entrada")
        self.scene = QGraphicsScene(self)
        self.graph = ZoomableGraphicsView(self.scene)
        self.graph.setMinimumHeight(560)
        panel.content.addLayout(_graph_controls(self.graph))
        panel.content.addWidget(self.graph, 1)
        layout.addWidget(panel, 1)
        self.result = QLabel("Analiza una cadena aceptada para construir su árbol.")
        self.result.setObjectName("muted")
        layout.addWidget(self.result)

    def set_analysis(self, analysis: Analysis | None) -> None:
        self.scene.clear()
        self.ast_node_items.clear()
        self.ast_root = None
        if analysis is None or analysis.parse_result.root is None:
            self.result.setText("No hay árbol: la entrada no fue aceptada.")
            return
        self.ast_root = analysis.parse_result.root
        self._draw_ast(self.ast_root)
        self.result.setText(
            f"AST de la entrada actual · {len(self.ast_node_items)} nodos reales · "
            "generado a partir de las reducciones del parser."
            + (f" Evaluación no disponible: {analysis.evaluation_error}."
               if analysis.evaluation_error else "")
        )
        self.graph.fit_scene()

    def _draw_ast(self, root: ASTNode) -> None:
        gap_x = 34.0
        gap_y = 140.0
        node_sizes: dict[int, tuple[float, float]] = {}
        subtree_widths: dict[int, float] = {}
        nodes: dict[int, ASTNode] = {}
        font = QFont("Segoe UI", 11, QFont.Weight.DemiBold)
        metrics = QFontMetricsF(font)

        def measure(node: ASTNode) -> float:
            nodes[id(node)] = node
            label = _ast_label(node)
            width = max(110.0, metrics.horizontalAdvance(label) + 32)
            height = 50.0
            node_sizes[id(node)] = (width, height)
            children = node.children or []
            if not children:
                subtree_widths[id(node)] = width
                return width
            child_width = sum(measure(child) for child in children) + gap_x * (len(children) - 1)
            subtree_widths[id(node)] = max(width, child_width)
            return subtree_widths[id(node)]

        measure(root)
        positions: dict[int, tuple[float, float]] = {}

        def place(node: ASTNode, left: float, depth: int) -> None:
            width, _ = node_sizes[id(node)]
            span = subtree_widths[id(node)]
            x = left + span / 2
            y = depth * gap_y + 55
            positions[id(node)] = (x, y)
            children = node.children or []
            if not children:
                return
            total = sum(subtree_widths[id(child)] for child in children) + gap_x * (len(children) - 1)
            child_left = left + (span - total) / 2
            for child in children:
                place(child, child_left, depth + 1)
                child_left += subtree_widths[id(child)] + gap_x

        place(root, 0, 0)
        for node_id, node in nodes.items():
            parent_position = positions[node_id]
            parent_height = node_sizes[node_id][1]
            for child in node.children or []:
                child_position = positions[id(child)]
                child_height = node_sizes[id(child)][1]
                line = QGraphicsLineItem(
                    parent_position[0],
                    parent_position[1] + parent_height / 2,
                    child_position[0],
                    child_position[1] - child_height / 2,
                )
                line.setPen(QPen(QColor("#aab8ca"), 2))
                line.setZValue(0)
                self.scene.addItem(line)

        for node_id, node in nodes.items():
            width, height = node_sizes[node_id]
            x, y = positions[node_id]
            category = _ast_category(node)
            fill, border = self._palette[category]
            rect = QGraphicsRectItem(QRectF(x - width / 2, y - height / 2, width, height))
            rect.setBrush(QBrush(QColor(fill)))
            rect.setPen(QPen(QColor(border), 2))
            rect.setZValue(1)
            self.scene.addItem(rect)
            label = QGraphicsSimpleTextItem(_ast_label(node))
            label.setFont(font)
            label.setBrush(QBrush(QColor("#20334d")))
            label.setPos(x - label.boundingRect().width() / 2, y - label.boundingRect().height() / 2)
            label.setZValue(2)
            self.scene.addItem(label)
            self.ast_node_items[node_id] = rect
        self.scene.setSceneRect(self.scene.itemsBoundingRect().adjusted(-45, -45, 45, 45))


class TestBankView(QWidget):
    VALID = [
        "1", "x", "2.5", "(3)", "1+2", "7-4", "3*8", "9/3",
        "a=5", "x=1+2", "2+3*4", "(2+3)*4", "8/4/2", "1-2-3",
        RecognizerView.EXAMPLE,
    ]
    INVALID = [
        "", "+1", "1+", "*2", "a=", "=2", "1 2", "(1+2", "1+2)",
        "a==2", "1*/2", "()", "1..2", "@", "x=1=2",
    ]

    def __init__(self, service: AnalyzerService):
        super().__init__()
        self.service = service
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 30)
        layout.setSpacing(18)
        layout.addWidget(
            PageHeader(
                "Banco de pruebas",
                "Ejecuta casos de entrada contra el mismo lexer, parser SLR(1) y servicio de análisis "
                "que utiliza el reconocedor.",
            )
        )
        summary_row = QHBoxLayout()
        summary_row.setSpacing(12)
        self.total_metric = MetricCard("Total", "—")
        self.passed_metric = MetricCard("Aprobadas", "—")
        self.failed_metric = MetricCard("Fallidas", "—")
        self.rate_metric = MetricCard("Aprobación", "—")
        for metric in (self.total_metric, self.passed_metric, self.failed_metric, self.rate_metric):
            summary_row.addWidget(metric, 1)
        layout.addLayout(summary_row)
        panel = Panel("Resultados por caso")
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            ["Prueba", "Cadena", "Esperado", "Obtenido", "Estado"]
        )
        self.table.setColumnWidth(0, 160)
        self.table.setColumnWidth(1, 450)
        self.table.setColumnWidth(2, 130)
        self.table.setColumnWidth(3, 190)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        panel.content.addWidget(self.table, 1)
        layout.addWidget(panel, 1)
        button = QPushButton("Ejecutar pruebas")
        button.setObjectName("primaryButton")
        button.clicked.connect(self.run_cases)
        layout.addWidget(button, alignment=Qt.AlignmentFlag.AlignLeft)
        self.run_cases()

    def run_cases(self) -> None:
        cases = [
            (f"Válida {index:02}", source, True)
            for index, source in enumerate(self.VALID, 1)
        ] + [
            (f"Inválida {index:02}", source, False)
            for index, source in enumerate(self.INVALID, 1)
        ]
        self.table.setRowCount(len(cases))
        passed = 0
        for row, (name, source, expected) in enumerate(cases):
            try:
                analysis = self.service.analyze(source)
                accepted = True
                obtained = "Aceptada" + (
                    " · sin evaluación" if analysis.evaluation_error else ""
                )
            except (LexerError, ParseError) as error:
                accepted = False
                obtained = f"Rechazada · {error}"
            success = accepted == expected
            passed += int(success)
            values = (
                name,
                source or "(vacía)",
                "Aceptada" if expected else "Rechazada",
                obtained,
                "PASÓ" if success else "FALLÓ",
            )
            for column, value in enumerate(values):
                item = _cell(value)
                if column == 4:
                    item.setBackground(QBrush(QColor("#e4f6ed" if success else "#fde9e7")))
                    item.setForeground(QBrush(QColor("#11764b" if success else "#b42318")))
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)
                self.table.setItem(row, column, item)
            self.table.setRowHeight(row, 48)
        total = len(cases)
        failed = total - passed
        self.total_metric.set_value(str(total))
        self.passed_metric.set_value(str(passed))
        self.failed_metric.set_value(str(failed))
        self.rate_metric.set_value(f"{passed / total * 100:.0f}%" if total else "0%")


def _ast_label(node: ASTNode) -> str:
    children = node.children or []
    if node.symbol == "S" and len(children) == 3 and children[1].symbol == "=":
        return "S · asignación"
    if node.symbol in {"E", "T"} and len(children) == 3:
        return f"{node.symbol} · operador {children[1].symbol}"
    if node.symbol == "F" and len(children) == 3:
        return "F · paréntesis"
    if node.symbol == "id":
        return f"id · {node.value or ''}"
    if node.symbol == "num":
        return f"num · {node.value or ''}"
    if node.symbol in {"+", "-", "*", "/"}:
        return f"operador · {node.symbol}"
    if node.symbol in {"=", "(", ")"}:
        return f"símbolo · {node.symbol}"
    if node.symbol == "S'":
        return "S' · aumentado"
    return node.symbol


def _ast_category(node: ASTNode) -> str:
    if node.symbol in {"+", "-", "*", "/"}:
        return "operator"
    if node.symbol in {"id", "num"}:
        return "operand"
    if node.symbol in {"=", "(", ")"}:
        return "punctuation"
    return "grammar"


def _prepare_table(table: QTableWidget) -> None:
    table.setAlternatingRowColors(True)
    table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
    table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    table.horizontalHeader().setMinimumHeight(40)
    table.verticalHeader().setVisible(False)


def _cell(text: str) -> QTableWidgetItem:
    item = QTableWidgetItem(text)
    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
    return item
