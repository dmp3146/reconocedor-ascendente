import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from app.main_window import MainWindow
from app.views import RecognizerView


@pytest.fixture(scope="session")
def qt_app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def window(qt_app):
    instance = MainWindow()
    yield instance
    instance.close()


def _ast_node_ids(root):
    result = {id(root)}
    for child in root.children or []:
        result.update(_ast_node_ids(child))
    return result


def test_main_window_has_seven_views_and_example_result(window):
    assert window.pages.count() == 7
    assert len(window.service.table.states) == 21

    window.recognizer.load_example(RecognizerView.EXAMPLE)
    window.recognizer.analyze()

    assert window.recognizer.result_status.text() == "CADENA ACEPTADA"
    assert window.recognizer.result_value.text() == "var = 40.0"
    assert window.recognizer.final_metric.value.text() == "ACCEPT"
    assert len(window.simulation.steps) > 0


def test_invalid_input_shows_parser_error_step_without_a_result(window):
    window.recognizer.load_example("1+")
    window.recognizer.analyze()

    assert window.recognizer.result_status.text() == "CADENA RECHAZADA"
    assert window.recognizer.final_metric.value.text() == "ERROR"
    assert "40.0" not in window.recognizer.result_value.text()
    assert window.simulation.error_message is not None
    assert window.simulation.steps

    window.simulation._run()
    assert window.simulation.table.item(
        window.simulation.table.rowCount() - 1, 5
    ).text() == "ERROR"


def test_valid_identifier_is_accepted_without_inventing_numeric_value(window):
    window.recognizer.load_example("x + 1")
    window.recognizer.analyze()

    assert window.recognizer.result_status.text() == "ERROR DE EVALUACIÓN"
    assert window.recognizer.result_value.text() == "NO EVALUABLE"
    assert "Análisis sintáctico: ACEPTADO" in window.recognizer.stage_summary.text()
    assert window.tree.ast_root is not None


def test_clear_resets_the_recognizer_and_simulation(window):
    window.recognizer.load_example("1 + 2")
    window.recognizer.analyze()
    window.recognizer.clear()

    assert window.recognizer.result_status.text() == "LISTO PARA ANALIZAR"
    assert window.recognizer.source.toPlainText() == ""
    assert window.simulation.input_label.text() == "Analiza una entrada para cargar la traza."
    assert window.tree.ast_root is None


def test_sidebar_toggle_preserves_view_and_analysis(window, qt_app):
    window.show()
    window.recognizer.load_example("10 / 2")
    window.recognizer.analyze()
    window.simulation._move(3)
    window.navigation.setCurrentRow(4)
    qt_app.processEvents()

    original_width = window.pages.width()
    original_tree = window.tree.ast_root
    original_trace = window.simulation.steps
    original_position = window.simulation.position
    assert window.sidebar.isVisible()
    assert not window.show_sidebar_button.isVisible()

    window.hide_sidebar_button.click()
    qt_app.processEvents()
    assert window.sidebar.isHidden()
    assert window.show_sidebar_button.isVisible()
    assert window.pages.width() > original_width
    assert window.pages.currentIndex() == window.navigation.currentRow() == 4
    assert window.recognizer.source.toPlainText() == "10 / 2"
    assert window.recognizer.result_value.text() == "5.0"
    assert window.tree.ast_root is original_tree
    assert window.simulation.steps is original_trace
    assert window.simulation.position == original_position

    window.show_sidebar_button.click()
    qt_app.processEvents()
    assert window.sidebar.isVisible()
    assert window.sidebar.width() == 260
    assert not window.show_sidebar_button.isVisible()
    assert window.pages.width() == original_width
    assert window.pages.currentIndex() == window.navigation.currentRow() == 4
    assert window.recognizer.source.toPlainText() == "10 / 2"
    assert window.recognizer.result_value.text() == "5.0"
    assert window.tree.ast_root is original_tree
    assert window.simulation.steps is original_trace
    assert window.simulation.position == original_position


@pytest.mark.parametrize(
    "source",
    ["1 + 1", "5 * 3", "(8 + 2) / 5", "10 / (4 - 4)", "5 + * 3"],
)
def test_automaton_route_matches_parser_trace(window, source):
    automaton = window.automaton
    table = window.service.table
    original_states = tuple(table.states)
    original_transitions = dict(table.transitions)
    window.recognizer.load_example(source)
    window.recognizer.analyze()

    trace = window.simulation.steps
    route = automaton.route_steps
    assert automaton.route_source == source
    assert tuple(table.states) == original_states
    assert table.transitions == original_transitions
    assert len(automaton.state_items) == len(original_states)
    assert len(route) == len(trace) + (1 if window.simulation.error_message else 0)
    for index, step in enumerate(trace):
        event = route[index]
        assert event.action == step.action.kind.upper()
        assert event.origin == step.states[-1]
        assert event.lookahead == step.remaining_input[0]
        if event.action == "SHIFT":
            assert event.transition_origin == step.states[-1]
            assert event.transition_symbol == step.remaining_input[0]
            assert event.destination == step.action.value
        elif event.action == "REDUCE":
            production = step.production
            assert event.transition_origin == step.states[-len(production.rhs) - 1]
            assert event.transition_symbol == production.lhs
            assert event.destination == table.goto[(event.transition_origin, production.lhs)]
            if index + 1 < len(trace):
                assert trace[index + 1].remaining_input == step.remaining_input
        else:
            assert event.action == "ACCEPT"
            assert event.destination is None
            assert event.transition_origin is None
        if event.transition_origin is not None:
            assert table.transitions[(event.transition_origin, event.transition_symbol)] == event.destination

    if source == "5 + * 3":
        assert route[-1].action == "ERROR"
        assert route[-1].lookahead == "*"
        assert route[-1].destination is None
        assert route[-1].transition_origin is None
        previous = route[-2]
        assert route[-1].origin == previous.destination
    else:
        assert route[-1].action == "ACCEPT"


def test_automaton_route_controls_and_reanalysis(window):
    automaton = window.automaton
    base_transitions = dict(window.service.table.transitions)
    window.recognizer.load_example("1 + 1")
    window.recognizer.analyze()
    assert automaton.route_position == 0
    assert automaton.state_items[0].brush().color().name() == "#ffe2b5"

    automaton.next_step_button.click()
    first = automaton.route_steps[0]
    assert automaton.route_position == 1
    assert automaton.state_items[first.destination].brush().color().name() == "#ffe2b5"
    assert automaton.state_items[0].brush().color().name() == "#d9f3e5"
    assert automaton.edge_items[(first.transition_origin, first.destination)][0].pen().widthF() == 4.5
    assert "Acción: SHIFT" in automaton.route_context.text()
    assert "Símbolo leído: num" in automaton.route_context.text()
    automaton.next_step_button.click()
    assert "Acción: REDUCE" in automaton.route_context.text()
    assert "Símbolo pendiente (no consumido): +" in automaton.route_context.text()
    automaton.previous_step_button.click()
    assert automaton.route_position == 1
    automaton.select_state(first.destination)
    assert window.service.table.state_items(first.destination)[0] in automaton.detail.toPlainText()
    assert automaton.state_items[first.destination].brush().color().name() == "#ffe2b5"

    automaton.full_route_button.click()
    assert automaton.route_position == len(automaton.route_steps)
    assert "Acción: ACCEPT" in automaton.route_context.text()
    automaton.show_automaton_button.click()
    assert not automaton.showing_route
    assert automaton.route_position == len(automaton.route_steps)
    automaton.reset_route_button.click()
    assert automaton.route_position == 0
    assert automaton.showing_route

    window.recognizer.load_example("5 * 3")
    window.recognizer.analyze()
    assert automaton.route_position == 0
    assert automaton.route_source == "5 * 3"
    assert window.service.table.transitions == base_transitions
    window.recognizer.load_example("5 + @")
    window.recognizer.analyze()
    assert not automaton.route_steps
    assert "parser no se ejecutó" in automaton.route_context.text()
    window.recognizer.clear()
    assert not automaton.route_steps
    assert automaton.route_source == ""


@pytest.mark.parametrize("source", ["10 / 0", "10 / (4 - 4)", "20 / (2 - 2)"])
def test_evaluation_error_keeps_ast_and_accept_trace(window, source):
    window.recognizer.load_example(source)
    window.recognizer.analyze()

    recognizer = window.recognizer
    assert recognizer.result_status.text() == "ERROR DE EVALUACIÓN"
    assert recognizer.result_value.text() == "NO EVALUABLE"
    assert recognizer.result_message.text() == (
        "Error semántico: división entre cero. La expresión es sintácticamente válida, "
        "pero no tiene un resultado numérico definido."
    )
    for text in (
        "Análisis léxico: CORRECTO", "Análisis sintáctico: ACEPTADO",
        "Árbol sintáctico: GENERADO", "Evaluación: ERROR", "Resultado final: NO EVALUABLE",
    ):
        assert text in recognizer.stage_summary.text()
    assert window.tree.ast_root is not None
    assert window.simulation.steps[-1].action.kind == "accept"
    assert recognizer.final_metric.value.text() == "ACCEPT"


def test_lexical_error_does_not_create_a_parser_error_step(window):
    window.recognizer.load_example("5 + @")
    window.recognizer.analyze()

    assert "Análisis léxico: ERROR" in window.recognizer.stage_summary.text()
    assert "Análisis sintáctico: NO EJECUTADO" in window.recognizer.stage_summary.text()
    assert window.simulation.total_rows == 0
    assert "parser no ejecutado" in window.simulation.input_label.text()
    assert window.simulation.current_state.text() == "PARSER NO EJECUTADO"
    assert window.tree.ast_root is None


def test_evaluation_error_replaces_previous_numeric_result(window):
    window.recognizer.load_example("10 / 2")
    window.recognizer.analyze()
    assert window.recognizer.result_value.text() == "5.0"
    window.recognizer.load_example("10 / 0")
    window.recognizer.analyze()
    assert window.recognizer.result_value.text() == "NO EVALUABLE"
    assert "5.0" not in window.recognizer.result_message.text()


def test_graphical_ast_contains_exactly_the_parser_ast_nodes(window):
    window.recognizer.load_example(RecognizerView.TREE_EXAMPLE)
    window.recognizer.analyze()

    root = window.tree.ast_root
    assert root is not None
    assert root.symbol == "S"
    assert set(window.tree.ast_node_items) == _ast_node_ids(root)
    assert any(node.symbol == "*" for node_id in window.tree.ast_node_items
               for node in _walk(root) if id(node) == node_id)
    assert window.tree.scene.items()


def _walk(node):
    yield node
    for child in node.children or []:
        yield from _walk(child)


def test_automaton_table_simulation_and_test_bank_use_real_engine(window):
    table = window.service.table
    assert len(window.pages.widget(2).widget().state_items) == len(table.states)
    state_to_inspect = next(state for state in range(len(table.states)) if table.state_items(state))
    window.pages.widget(2).widget().select_state(state_to_inspect)
    assert table.state_items(state_to_inspect)[0] in window.pages.widget(2).widget().detail.toPlainText()

    assert window.pages.widget(3).widget().table.rowCount() == len(table.states) + 2
    window.recognizer.load_example("2 + 3 * 4")
    window.recognizer.analyze()
    action_kinds = {step.action.kind for step in window.simulation.steps if step.action}
    assert {"shift", "reduce", "accept"} <= action_kinds
    assert window.pages.widget(6).widget().passed_metric.value.text() == "30"
    assert window.pages.widget(6).widget().failed_metric.value.text() == "0"
