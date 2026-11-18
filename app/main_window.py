import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QScrollArea,
    QStackedWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from app.views import (
    AutomatonView,
    GrammarView,
    RecognizerView,
    SimulationView,
    SyntaxTreeView,
    TableView,
    TestBankView,
)
from parsers.ascending.parser import ParseError
from services.analyzer_service import AnalyzerService


class MainWindow(QMainWindow):
    NAV_ITEMS = (
        ("01", "Reconocedor"),
        ("02", "Gramática"),
        ("03", "Autómata LR(0)"),
        ("04", "Tabla ACTION/GOTO"),
        ("05", "Simulación"),
        ("06", "Árbol sintáctico"),
        ("07", "Banco de pruebas"),
    )

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Reconocedor Ascendente SLR(1)")
        screen = QGuiApplication.primaryScreen()
        available = screen.availableGeometry() if screen else None
        width = available.width() if available else 1600
        height = available.height() if available else 1000
        self.setMinimumSize(min(1180, width), min(740, height))
        self.resize(min(1450, width), min(900, height))
        self.service = AnalyzerService()

        central = QWidget()
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        self.navigation = QListWidget()
        self.navigation.setObjectName("navigation")
        self.navigation.setFixedWidth(260)
        self.navigation.setSpacing(5)
        self.sidebar = QWidget()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(260)
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(14, 18, 14, 20)
        sidebar_layout.setSpacing(14)
        brand = QLabel("RA")
        brand.setObjectName("brandMark")
        brand.setAlignment(Qt.AlignmentFlag.AlignCenter)
        brand.setFixedSize(56, 56)
        brand_title = QLabel("LABORATORIO\nDE LENGUAJES")
        brand_title.setObjectName("brandTitle")
        self.hide_sidebar_button = QToolButton()
        self.hide_sidebar_button.setObjectName("hideSidebarButton")
        self.hide_sidebar_button.setText("◀")
        self.hide_sidebar_button.setToolTip("Ocultar menú lateral")
        self.hide_sidebar_button.setAccessibleName("Ocultar menú lateral")
        self.hide_sidebar_button.setFixedSize(34, 34)
        self.hide_sidebar_button.clicked.connect(self._hide_sidebar)
        brand_row = QHBoxLayout()
        brand_row.addWidget(brand)
        brand_row.addWidget(brand_title, 1)
        brand_row.addWidget(self.hide_sidebar_button)
        sidebar_layout.addLayout(brand_row)
        section_label = QLabel("ANÁLISIS SLR(1)")
        section_label.setObjectName("sidebarSection")
        sidebar_layout.addWidget(section_label)
        for number, name in self.NAV_ITEMS:
            item = QListWidgetItem(f"{number}    {name}")
            self.navigation.addItem(item)
        sidebar_layout.addWidget(self.navigation, 1)
        sidebar_note = QLabel("ANÁLISIS ASCENDENTE\nCLOSURE · GOTO · ACTION")
        sidebar_note.setObjectName("sidebarNote")
        sidebar_layout.addWidget(sidebar_note)
        root.addWidget(self.sidebar)

        self.pages = QStackedWidget()
        self.simulation = SimulationView(self.service)
        self.tree = SyntaxTreeView(self.service)
        self.automaton = AutomatonView(self.service)
        self.recognizer = RecognizerView(self.service, self._publish_analysis)
        page_widgets = [
            self.recognizer,
            GrammarView(self.service),
            self.automaton,
            TableView(self.service),
            self.simulation,
            self.tree,
            TestBankView(self.service),
        ]
        self.page_scroll_areas: list[QScrollArea] = []
        for page in page_widgets:
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QFrame.Shape.NoFrame)
            scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
            scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
            scroll.setWidget(page)
            self.page_scroll_areas.append(scroll)
            self.pages.addWidget(scroll)

        workspace = QWidget()
        workspace_layout = QVBoxLayout(workspace)
        workspace_layout.setContentsMargins(0, 0, 0, 0)
        workspace_layout.setSpacing(0)
        topbar = QWidget()
        topbar.setObjectName("topbar")
        topbar_layout = QHBoxLayout(topbar)
        topbar_layout.setContentsMargins(26, 12, 28, 12)
        self.show_sidebar_button = QToolButton()
        self.show_sidebar_button.setObjectName("showSidebarButton")
        self.show_sidebar_button.setText("☰")
        self.show_sidebar_button.setToolTip("Mostrar menú lateral")
        self.show_sidebar_button.setAccessibleName("Mostrar menú lateral")
        self.show_sidebar_button.setFixedSize(36, 36)
        self.show_sidebar_button.clicked.connect(self._show_sidebar)
        self.show_sidebar_button.hide()
        breadcrumb = QLabel("TEORÍA DE LENGUAJES    /    RECONOCEDOR ASCENDENTE")
        breadcrumb.setObjectName("breadcrumb")
        self.header_status = QLabel(
            f"● MOTOR ACTIVO  ·  {len(self.service.table.states)} ESTADOS"
        )
        self.header_status.setObjectName("headerStatus")
        topbar_layout.addWidget(self.show_sidebar_button)
        topbar_layout.addWidget(breadcrumb)
        topbar_layout.addStretch(1)
        topbar_layout.addWidget(self.header_status)
        workspace_layout.addWidget(topbar)
        workspace_layout.addWidget(self.pages, 1)
        root.addWidget(workspace, 1)

        self.navigation.currentRowChanged.connect(self.pages.setCurrentIndex)
        self.navigation.setCurrentRow(0)
        self.setCentralWidget(central)
        self.setStyleSheet(
            """
            * { font-family: "Segoe UI"; }
            QMainWindow, QWidget { background: #f3f6fb; color: #1d2939; font-size: 11pt; }
            #sidebar { background: #11233d; }
            QToolButton#hideSidebarButton { background: #254c7e; color: white;
                                            border: 0; border-radius: 6px; font-size: 11pt; }
            QToolButton#hideSidebarButton:hover { background: #376498; }
            QToolButton#showSidebarButton { background: #eaf1fa; color: #234a76;
                                            border: 1px solid #d8e1ee; border-radius: 6px;
                                            font-size: 14pt; }
            QToolButton#showSidebarButton:hover { background: #dce8f6; }
            #brandMark { background: #2c5eaa; color: white; border-radius: 12px;
                         font-size: 19pt; font-weight: 800; }
            #brandTitle { color: #edf3fd; font-size: 10pt; font-weight: 700; letter-spacing: 1px; }
            #sidebarSection { color: #8ea5c5; font-size: 9pt; font-weight: 700;
                              padding: 18px 10px 4px; }
            #navigation { background: transparent; color: #d3deec; border: 0;
                          outline: 0; padding: 2px; font-size: 10.5pt; }
            #navigation::item { min-height: 48px; padding: 4px 11px; border-radius: 7px; }
            #navigation::item:selected { background: #254c7e; color: white; font-weight: 700; }
            #navigation::item:hover:!selected { background: #1b3555; }
            #sidebarNote { color: #8ea5c5; font-size: 8.5pt; line-height: 150%;
                           padding: 13px 10px; border-top: 1px solid #263d5a; }
            #topbar { background: white; border-bottom: 1px solid #e1e7f0; }
            #breadcrumb { color: #63748b; font-size: 9pt; font-weight: 700; letter-spacing: .5px; }
            #headerStatus, #engineStatus, #successBadge { color: #167447; background: #e4f6ed;
                          border: 1px solid #cae9d8; border-radius: 15px; padding: 7px 13px;
                          font-size: 9pt; font-weight: 700; }
            #pageTitle { color: #15345d; font-size: 25pt; font-weight: 750; }
            #muted { color: #68788e; font-size: 10.5pt; }
            #panel { background: white; border: 1px solid #e1e7f0; border-radius: 12px; }
            #panelTitle { color: #1d3658; font-size: 14pt; font-weight: 700; }
            #metricCard { background: white; border: 1px solid #dfe7f1; border-radius: 10px; }
            #metricTitle { color: #75849a; font-size: 8pt; font-weight: 700; letter-spacing: .7px; }
            #metricValue { color: #173a68; font-size: 17pt; font-weight: 700; }
            QPushButton { background: #2857a4; color: white; border: 1px solid #2857a4;
                          border-radius: 7px; padding: 10px 16px; font-size: 10.5pt; font-weight: 650; }
            QPushButton:hover { background: #214984; }
            QPushButton:pressed { background: #173963; }
            QPushButton:disabled { background: #c3ccda; color: #f7f8fa; border-color: #c3ccda; }
            QPushButton#secondaryButton { background: #f1f5fb; color: #294b77;
                          border: 1px solid #d8e1ee; }
            QPushButton#secondaryButton:hover { background: #e6eef8; }
            QPushButton#primaryButton { padding: 11px 22px; }
            #sourceEditor, #stateDetails { background: #fbfcfe; color: #142238;
                          border: 1px solid #d4dfed; border-radius: 8px; padding: 13px;
                          font-size: 15pt; }
            #sourceEditor { font-family: "Cascadia Code", "Consolas", monospace; }
            #resultPanel[status="accepted"] { border: 2px solid #43a979; }
            #resultPanel[status="rejected"] { border: 2px solid #d6675e; }
            #resultPanel[status="evaluationError"] { border: 2px solid #d49a20; }
            #resultStatus { color: #68788e; font-size: 13pt; font-weight: 800; letter-spacing: 1px; }
            #resultPanel[status="accepted"] #resultStatus { color: #11764b; }
            #resultPanel[status="rejected"] #resultStatus { color: #b42318; }
            #resultPanel[status="evaluationError"] #resultStatus { color: #925b00; }
            #resultValue { color: #153d70; font-size: 31pt; font-weight: 750; }
            #resultPanel[status="rejected"] #resultValue { color: #b42318; font-size: 22pt; }
            #resultPanel[status="evaluationError"] #resultValue { color: #925b00; font-size: 22pt; }
            #resultExpression { color: #47576d; font-size: 11pt; }
            #resultMessage { color: #53647b; font-size: 10.5pt; }
            #tokenLine { color: #395b88; font-family: "Cascadia Code", "Consolas", monospace;
                         font-size: 9.5pt; padding-top: 4px; }
            #symbolSummary { color: #395b78; background: #edf3fa; border-radius: 7px;
                             padding: 10px 13px; font-family: "Cascadia Code", "Consolas", monospace; }
            QTableWidget { background: white; alternate-background-color: #f7f9fc;
                           border: 1px solid #e0e7f0; border-radius: 7px; gridline-color: #e8edf4;
                           selection-background-color: #dbeafe; selection-color: #17345c; font-size: 10pt; }
            QHeaderView::section { background: #eaf0f8; color: #29466d; padding: 9px 7px;
                           border: 0; border-right: 1px solid #dce5f0; font-size: 9pt; font-weight: 750; }
            QTableCornerButton::section { background: #eaf0f8; border: 0; }
            #lrTable QTableWidgetItem { padding: 6px; }
            #graphicsCanvas { background: #fbfcfe; border: 1px solid #e0e7f0; border-radius: 8px; }
            #simulationInput { background: #eaf1fa; color: #234a76; border-radius: 7px;
                               padding: 12px 15px; font-weight: 650; }
            #stateBadge { background: #eaf1fa; color: #1b4e83; border-radius: 7px;
                          padding: 10px 14px; font-weight: 750; }
            #actionExplanation { color: #354960; font-size: 11pt; padding: 4px; }
            QScrollBar:vertical { width: 13px; background: #eff3f8; margin: 0; }
            QScrollBar::handle:vertical { background: #bac8d9; min-height: 30px; border-radius: 6px; }
            QScrollBar:horizontal { height: 13px; background: #eff3f8; margin: 0; }
            QScrollBar::handle:horizontal { background: #bac8d9; min-width: 30px; border-radius: 6px; }
            """
        )

    def _hide_sidebar(self) -> None:
        self.sidebar.hide()
        self.show_sidebar_button.show()

    def _show_sidebar(self) -> None:
        self.show_sidebar_button.hide()
        self.sidebar.show()

    def _publish_analysis(self, analysis, error, source: str) -> None:
        self.automaton.set_analysis(analysis, error, source)
        if analysis is not None:
            self.simulation.set_analysis(analysis)
            self.tree.set_analysis(analysis)
        elif error is not None:
            self.simulation.set_rejection(source, error)
            self.tree.set_analysis(None)
        else:
            self.simulation.set_analysis(None)
            self.tree.set_analysis(None)


def run() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Reconocedor Ascendente")
    window = MainWindow()
    screen = QGuiApplication.primaryScreen()
    available = screen.availableGeometry() if screen else None
    if available and available.width() >= 1650 and available.height() >= 980:
        window.showMaximized()
    else:
        window.show()
    return app.exec()
