import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QStackedWidget,
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
from services.analyzer_service import AnalyzerService


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Reconocedor Ascendente · SLR(1)")
        self.resize(1240, 820)
        self.service = AnalyzerService()

        central = QWidget()
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        self.navigation = QListWidget()
        self.navigation.setObjectName("navigation")
        self.navigation.setFixedWidth(235)
        sidebar = QVBoxLayout()
        brand = QLabel("RA\nRECONOCEDOR\nASCENDENTE")
        brand.setObjectName("brand")
        brand.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sidebar.addWidget(brand)
        sidebar.addWidget(self.navigation)
        sidebar_widget = QWidget()
        sidebar_widget.setLayout(sidebar)
        root.addWidget(sidebar_widget)

        self.pages = QStackedWidget()
        self.simulation = SimulationView(self.service)
        self.tree = SyntaxTreeView(self.service)
        self.recognizer = RecognizerView(self.service, self._publish_analysis)
        pages = [
            ("Reconocedor", self.recognizer),
            ("Gramática", GrammarView(self.service)),
            ("Autómata LR", AutomatonView(self.service)),
            ("Tabla ACTION/GOTO", TableView(self.service)),
            ("Simulación", self.simulation),
            ("Árbol sintáctico", self.tree),
            ("Banco de pruebas", TestBankView(self.service)),
        ]
        for name, page in pages:
            item = QListWidgetItem(name)
            self.navigation.addItem(item)
            self.pages.addWidget(page)
        self.navigation.currentRowChanged.connect(self.pages.setCurrentIndex)
        self.navigation.setCurrentRow(0)
        root.addWidget(self.pages, 1)
        self.setCentralWidget(central)
        self.setStyleSheet(
            """
            QMainWindow, QWidget { background: #f5f7fb; color: #1d2939; font: 10pt "Segoe UI"; }
            #navigation { background: #15243b; color: #dce5f2; border: 0; padding: 10px; }
            #navigation::item { padding: 13px 10px; border-radius: 6px; }
            #navigation::item:selected { background: #2f5ca8; color: white; }
            #brand { background: #15243b; color: white; font-size: 15pt; font-weight: 700; padding: 22px 4px; }
            #pageTitle { font-size: 21pt; font-weight: 700; color: #17345c; padding: 8px 0; }
            QPushButton { background: #2857a4; color: white; border: 0; border-radius: 5px; padding: 9px 15px; }
            QPushButton:disabled { background: #aab6c8; }
            QPlainTextEdit, QTableWidget, QTreeWidget, QGraphicsView { background: white; border: 1px solid #d5deeb; border-radius: 4px; }
            QHeaderView::section { background: #e8eef7; padding: 6px; border: 0; font-weight: 600; }
            #result[valid="true"] { color: #167447; font-weight: 700; padding: 10px; }
            #result[valid="false"] { color: #b42318; font-weight: 700; padding: 10px; }
            """
        )

    def _publish_analysis(self, analysis) -> None:
        self.simulation.set_analysis(analysis)
        self.tree.set_analysis(analysis)


def run() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Reconocedor Ascendente")
    window = MainWindow()
    window.show()
    return app.exec()
