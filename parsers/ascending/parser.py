from dataclasses import dataclass

from grammar.grammar import Production
from lexer.tokens import Token
from parsers.ascending.slr import Action, SLRTable


@dataclass
class ASTNode:
    symbol: str
    value: str | None = None
    children: list["ASTNode"] | None = None

    def __post_init__(self) -> None:
        if self.children is None:
            self.children = []


@dataclass
class TraceStep:
    number: int
    states: tuple[int, ...]
    symbols: tuple[str, ...]
    remaining_input: tuple[str, ...]
    action: Action | None
    production: Production | None
    explanation: str


class ParseError(ValueError):
    def __init__(self, message: str, token: Token, expected: set[str]):
        self.token = token
        self.expected = expected
        expected_text = ", ".join(sorted(expected)) or "(ninguno)"
        found = token.lexeme if token.lexeme else "$"
        super().__init__(
            f"{message} en línea {token.line}, columna {token.column}; "
            f"se encontró {found!r}. Esperado: {expected_text}"
        )


@dataclass
class ParseResult:
    accepted: bool
    root: ASTNode | None
    trace: list[TraceStep]


class SLRParser:
    def __init__(self, table: SLRTable):
        self.table = table

    def parse(self, tokens: list[Token]) -> ParseResult:
        if not tokens or tokens[-1].symbol != self.table.grammar.end_marker:
            raise ValueError("La secuencia de tokens debe terminar con EOF ($)")

        states = [0]
        symbols: list[str] = []
        nodes: list[ASTNode] = []
        cursor = 0
        trace: list[TraceStep] = []
        step_number = 0

        while True:
            token = tokens[cursor]
            current_state = states[-1]
            selected = self.table.action.get((current_state, token.symbol))
            remaining = tuple(item.symbol for item in tokens[cursor:])
            if selected is None:
                expected = {
                    symbol
                    for (state, symbol) in self.table.action
                    if state == current_state
                }
                raise ParseError("Error sintáctico", token, expected)

            states_before = tuple(states)
            symbols_before = tuple(symbols)
            production = None
            if selected.kind == "shift":
                states.append(int(selected.value))
                symbols.append(token.symbol)
                nodes.append(ASTNode(token.symbol, token.lexeme))
                cursor += 1
                explanation = (
                    f"SHIFT: consumir {token.lexeme!r} y apilar el estado "
                    f"{selected.value}."
                )
            elif selected.kind == "reduce":
                production = self.table.grammar.productions[int(selected.value)]
                count = len(production.rhs)
                children = nodes[-count:] if count else []
                if count:
                    del nodes[-count:]
                    del symbols[-count:]
                    del states[-count:]
                node = ASTNode(production.lhs, children=children)
                target = self.table.goto.get((states[-1], production.lhs))
                if target is None:
                    raise RuntimeError(
                        f"Falta GOTO para el estado {states[-1]} y {production.lhs}"
                    )
                nodes.append(node)
                symbols.append(production.lhs)
                states.append(target)
                explanation = (
                    f"REDUCE por {production}: retirar {count} símbolo(s), "
                    f"consultar GOTO({states[-2]}, {production.lhs}) = {target}."
                )
            else:
                trace.append(
                    TraceStep(
                        step_number,
                        states_before,
                        symbols_before,
                        remaining,
                        selected,
                        None,
                        "ACCEPT: la entrada completa pertenece a la gramática.",
                    )
                )
                return ParseResult(True, nodes[-1] if nodes else None, trace)

            trace.append(
                TraceStep(
                    step_number,
                    states_before,
                    symbols_before,
                    remaining,
                    selected,
                    production,
                    explanation,
                )
            )
            step_number += 1
