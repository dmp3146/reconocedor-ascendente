from dataclasses import dataclass

from evaluator.evaluator import evaluate
from grammar.grammar import build_arithmetic_grammar
from lexer.lexer import Lexer
from lexer.tokens import Token
from parsers.ascending.parser import ParseResult, SLRParser
from parsers.ascending.slr import SLRGenerator, SLRTable


@dataclass
class Analysis:
    source: str
    tokens: list[Token]
    parse_result: ParseResult
    variable: str | None
    value: float


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
        variable, value = evaluate(result.root)
        return Analysis(source, tokens, result, variable, value)
