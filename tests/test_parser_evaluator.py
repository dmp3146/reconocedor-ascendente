import pytest

from evaluator.evaluator import EvaluationError, evaluate
from lexer.lexer import Lexer
from parsers.ascending.parser import ParseError, SLRParser
from parsers.ascending.slr import SLRGenerator
from grammar.grammar import build_arithmetic_grammar


@pytest.fixture(scope="module")
def parser():
    return SLRParser(SLRGenerator(build_arithmetic_grammar()).build())


VALID = [
    "1", "x", "2.5", "(3)", "1+2", "7-4", "3*8", "9/3",
    "a=5", "x=1+2", "2+3*4", "(2+3)*4", "8/4/2", "1-2-3",
    "var = 5.0 + 7.0 * (3.0 + 8.0 / 4.0)",
]
INVALID = [
    "", "+1", "1+", "*2", "a=", "=2", "1 2", "(1+2", "1+2)",
    "a==2", "1*/2", "()", "1..2", "@", "x=1=2",
]


@pytest.mark.parametrize("source", VALID)
def test_parser_accepts_valid_inputs(parser, source):
    result = parser.parse(Lexer().tokenize(source))
    assert result.accepted
    assert result.root is not None
    assert result.trace[-1].action.kind == "accept"


@pytest.mark.parametrize("source", INVALID)
def test_parser_rejects_invalid_syntax(parser, source):
    with pytest.raises((ParseError, ValueError)):
        parser.parse(Lexer().tokenize(source))


def test_parser_records_shifts_reductions_and_ast_precedence(parser):
    result = parser.parse(Lexer().tokenize("2+3*4"))
    kinds = [step.action.kind for step in result.trace]
    assert "shift" in kinds
    assert "reduce" in kinds
    root = result.root
    assert root.symbol == "S"
    assert root.children[0].symbol == "E"
    variable, value = evaluate(root)
    assert variable is None
    assert value == 14.0


def test_assignment_example_evaluates_to_expected_result(parser):
    result = parser.parse(
        Lexer().tokenize("var = 5.0 + 7.0 * (3.0 + 8.0 / 4.0)")
    )
    assert evaluate(result.root) == ("var", 40.0)


def test_trace_records_configuration_before_each_action(parser):
    result = parser.parse(Lexer().tokenize("2+3"))
    assert result.trace[0].states == (0,)
    assert result.trace[0].symbols == ()
    assert result.trace[0].remaining_input[0] == "num"
    assert result.trace[-1].action.kind == "accept"


def test_identifiers_without_assignment_cannot_be_evaluated():
    root = SLRParser(SLRGenerator(build_arithmetic_grammar()).build()).parse(
        Lexer().tokenize("x+1")
    ).root
    with pytest.raises(EvaluationError, match="sin un entorno"):
        evaluate(root)
