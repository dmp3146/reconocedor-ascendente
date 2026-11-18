from dataclasses import dataclass
from enum import Enum

from evaluator.evaluator import DivisionByZeroError, EvaluationError, evaluate
from grammar.grammar import build_arithmetic_grammar
from lexer.lexer import Lexer, LexerError
from lexer.tokens import Token
from parsers.ascending.parser import ParseError, ParseResult, SLRParser
from parsers.ascending.slr import SLRGenerator, SLRTable


@dataclass
class Analysis:
    source: str
    tokens: list[Token]
    parse_result: ParseResult
    variable: str | None
    value: float | None
    evaluation_error: str | None = None
    division_by_zero: bool = False


class StageStatus(str, Enum):
    NOT_RUN = "NO EJECUTADO"
    CORRECT = "CORRECTO"
    ACCEPTED = "ACEPTADO"
    ERROR = "ERROR"


@dataclass(frozen=True)
class AnalysisStages:
    lexical: StageStatus
    syntactic: StageStatus
    evaluation: StageStatus
    analysis: Analysis | None = None
    error: LexerError | ParseError | None = None


class AnalyzerService:
    def __init__(self):
        self.lexer = Lexer()
        self.table: SLRTable = SLRGenerator(build_arithmetic_grammar()).build()
        self.parser = SLRParser(self.table)

    def analyze(self, source: str) -> Analysis:
        tokens = self.lexer.tokenize(source)
        result = self.parser.parse(tokens)
        if result.root is None:
            raise RuntimeError("El parser aceptó la entrada sin producir un AST")
        try:
            variable, value = evaluate(result.root)
        except EvaluationError as error:
            return Analysis(
                source, tokens, result, None, None, str(error),
                isinstance(error, DivisionByZeroError),
            )
        return Analysis(source, tokens, result, variable, value)

    def analyze_stages(self, source: str) -> AnalysisStages:
        try:
            analysis = self.analyze(source)
        except LexerError as error:
            return AnalysisStages(
                StageStatus.ERROR, StageStatus.NOT_RUN, StageStatus.NOT_RUN,
                error=error,
            )
        except ParseError as error:
            return AnalysisStages(
                StageStatus.CORRECT, StageStatus.ERROR, StageStatus.NOT_RUN,
                error=error,
            )
        evaluation = (
            StageStatus.ERROR if analysis.evaluation_error is not None
            else StageStatus.CORRECT
        )
        return AnalysisStages(
            StageStatus.CORRECT, StageStatus.ACCEPTED, evaluation, analysis=analysis
        )
