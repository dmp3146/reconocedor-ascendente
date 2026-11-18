from dataclasses import dataclass


@dataclass(frozen=True)
class Production:
    index: int
    lhs: str
    rhs: tuple[str, ...]

    def __str__(self) -> str:
        return f"{self.lhs} → {' '.join(self.rhs)}"


class Grammar:
    def __init__(
        self,
        start_symbol: str,
        productions: list[tuple[str, tuple[str, ...]]],
        terminals: set[str],
        end_marker: str = "$",
    ):
        self.start_symbol = start_symbol
        self.end_marker = end_marker
        self.productions = [
            Production(index, lhs, tuple(rhs))
            for index, (lhs, rhs) in enumerate(productions)
        ]
        self.nonterminals = {lhs for lhs, _ in productions}
        self.terminals = set(terminals) | {end_marker}
        self.symbols = self.terminals | self.nonterminals
        self.by_lhs: dict[str, list[Production]] = {
            symbol: [] for symbol in self.nonterminals
        }
        for production in self.productions:
            self.by_lhs[production.lhs].append(production)

        if not self.productions or self.productions[0].lhs != start_symbol:
            raise ValueError("La primera producción debe ser la gramática aumentada")
        for production in self.productions:
            unknown = set(production.rhs) - self.symbols
            if unknown:
                raise ValueError(f"Símbolos no declarados en la gramática: {unknown}")

    def first_sets(self) -> dict[str, set[str]]:
        first = {symbol: set() for symbol in self.symbols}
        for terminal in self.terminals:
            first[terminal].add(terminal)

        changed = True
        while changed:
            changed = False
            for production in self.productions:
                before = len(first[production.lhs])
                if production.rhs:
                    first[production.lhs].update(first[production.rhs[0]])
                changed |= len(first[production.lhs]) != before
        return first

    def follow_sets(self) -> dict[str, set[str]]:
        follow = {symbol: set() for symbol in self.nonterminals}
        follow[self.start_symbol].add(self.end_marker)

        changed = True
        while changed:
            changed = False
            for production in self.productions:
                for position, symbol in enumerate(production.rhs):
                    if symbol not in self.nonterminals:
                        continue
                    before = len(follow[symbol])
                    suffix = production.rhs[position + 1 :]
                    if suffix:
                        follow[symbol].update(self.first_sets()[suffix[0]])
                    else:
                        follow[symbol].update(follow[production.lhs])
                    changed |= len(follow[symbol]) != before
        return follow


def build_arithmetic_grammar() -> Grammar:
    productions = [
        ("S'", ("S",)),
        ("S", ("id", "=", "E")),
        ("S", ("E",)),
        ("E", ("E", "+", "T")),
        ("E", ("E", "-", "T")),
        ("E", ("T",)),
        ("T", ("T", "*", "F")),
        ("T", ("T", "/", "F")),
        ("T", ("F",)),
        ("F", ("(", "E", ")")),
        ("F", ("id",)),
        ("F", ("num",)),
    ]
    terminals = {"id", "num", "=", "+", "-", "*", "/", "(", ")"}
    return Grammar("S'", productions, terminals)
