import pytest

from grammar.grammar import Grammar, build_arithmetic_grammar
from parsers.ascending.slr import GrammarConflictError, LRItem, SLRGenerator


def test_grammar_productions_and_first_follow():
    grammar = build_arithmetic_grammar()
    assert len(grammar.productions) == 12
    assert grammar.productions[0].lhs == "S'"
    first = grammar.first_sets()
    follow = grammar.follow_sets()
    assert first["E"] == {"id", "num", "("}
    assert "$" in follow["S'"]
    assert {"+", "-", ")", "$"} <= follow["E"]
    assert {"*", "/", "+", "-", ")", "$"} <= follow["T"]


def test_closure_and_goto_are_generated_from_lr_items():
    generator = SLRGenerator(build_arithmetic_grammar())
    initial = generator.closure({LRItem(0, 0)})
    assert LRItem(0, 0) in initial
    assert LRItem(1, 0) in initial
    assert LRItem(2, 0) in initial
    after_identifier = generator.goto(initial, "id")
    assert LRItem(10, 1) in after_identifier
    assert LRItem(1, 1) in after_identifier


def test_slr_automaton_and_table_have_real_transitions():
    table = SLRGenerator(build_arithmetic_grammar()).build()
    assert len(table.states) > 10
    assert table.transitions[(0, "id")] >= 0
    assert table.transitions[(0, "E")] >= 0
    assert table.action[(table.transitions[(0, "num")], "$")].kind == "reduce"
    assert any(action.kind == "accept" for action in table.action.values())
    assert any(action.kind == "shift" for action in table.action.values())
    assert any(action.kind == "reduce" for action in table.action.values())


def test_slr_generator_reports_shift_reduce_conflicts():
    grammar = Grammar(
        "S'",
        [
            ("S'", ("S",)),
            ("S", ("E",)),
            ("E", ("E", "+", "E")),
            ("E", ("id",)),
        ],
        {"id", "+"},
    )
    with pytest.raises(GrammarConflictError, match="Conflicto SLR"):
        SLRGenerator(grammar).build()
