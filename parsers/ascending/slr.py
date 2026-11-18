from collections import deque
from dataclasses import dataclass

from grammar.grammar import Grammar, Production


@dataclass(frozen=True, order=True)
class LRItem:
    production_index: int
    dot: int


@dataclass(frozen=True)
class Action:
    kind: str
    value: int | None = None

    def __str__(self) -> str:
        if self.kind == "shift":
            return f"s{self.value}"
        if self.kind == "reduce":
            return f"r{self.value}"
        return self.kind.upper()


class GrammarConflictError(ValueError):
    pass


@dataclass
class SLRTable:
    grammar: Grammar
    states: list[frozenset[LRItem]]
    transitions: dict[tuple[int, str], int]
    action: dict[tuple[int, str], Action]
    goto: dict[tuple[int, str], int]
    follow: dict[str, set[str]]

    def state_items(self, state: int) -> list[str]:
        result = []
        for item in sorted(self.states[state]):
            production = self.grammar.productions[item.production_index]
            rhs = list(production.rhs)
            rhs.insert(item.dot, "·")
            result.append(f"{production.lhs} → {' '.join(rhs)}")
        return result


class SLRGenerator:
    def __init__(self, grammar: Grammar):
        self.grammar = grammar

    def closure(self, items: set[LRItem] | frozenset[LRItem]) -> frozenset[LRItem]:
        result = set(items)
        changed = True
        while changed:
            changed = False
            for item in tuple(result):
                production = self.grammar.productions[item.production_index]
                if item.dot >= len(production.rhs):
                    continue
                symbol = production.rhs[item.dot]
                if symbol in self.grammar.nonterminals:
                    for child in self.grammar.by_lhs[symbol]:
                        candidate = LRItem(child.index, 0)
                        if candidate not in result:
                            result.add(candidate)
                            changed = True
        return frozenset(result)

    def goto(self, items: frozenset[LRItem], symbol: str) -> frozenset[LRItem]:
        moved = set()
        for item in items:
            production = self.grammar.productions[item.production_index]
            if item.dot < len(production.rhs) and production.rhs[item.dot] == symbol:
                moved.add(LRItem(item.production_index, item.dot + 1))
        return self.closure(moved) if moved else frozenset()

    def build(self) -> SLRTable:
        initial = self.closure({LRItem(0, 0)})
        states = [initial]
        state_ids = {initial: 0}
        transitions: dict[tuple[int, str], int] = {}
        pending = deque([0])
        symbols = sorted(self.grammar.symbols - {self.grammar.end_marker})

        while pending:
            state_id = pending.popleft()
            for symbol in symbols:
                target_items = self.goto(states[state_id], symbol)
                if not target_items:
                    continue
                if target_items not in state_ids:
                    state_ids[target_items] = len(states)
                    states.append(target_items)
                    pending.append(state_ids[target_items])
                transitions[(state_id, symbol)] = state_ids[target_items]

        follow = self.grammar.follow_sets()
        action: dict[tuple[int, str], Action] = {}
        goto_table: dict[tuple[int, str], int] = {}

        def add_action(key: tuple[int, str], value: Action) -> None:
            previous = action.get(key)
            if previous is not None and previous != value:
                raise GrammarConflictError(
                    f"Conflicto SLR en estado {key[0]}, símbolo {key[1]!r}: "
                    f"{previous} frente a {value}"
                )
            action[key] = value

        for state_id, items in enumerate(states):
            for item in items:
                production = self.grammar.productions[item.production_index]
                if item.dot < len(production.rhs):
                    symbol = production.rhs[item.dot]
                    target = transitions[(state_id, symbol)]
                    if symbol in self.grammar.terminals - {self.grammar.end_marker}:
                        add_action((state_id, symbol), Action("shift", target))
                    else:
                        goto_table[(state_id, symbol)] = target
                elif item.production_index == 0:
                    add_action((state_id, self.grammar.end_marker), Action("accept"))
                else:
                    for terminal in follow[production.lhs]:
                        add_action((state_id, terminal), Action("reduce", production.index))

        return SLRTable(
            self.grammar,
            states,
            transitions,
            action,
            goto_table,
            follow,
        )
