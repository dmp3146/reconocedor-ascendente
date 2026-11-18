from lexer.tokens import TokenType
from parsers.ascending.parser import ASTNode


class EvaluationError(ValueError):
    pass


class DivisionByZeroError(EvaluationError):
    pass


def evaluate(root: ASTNode) -> tuple[str | None, float]:
    if root.symbol == "S" and len(root.children) == 3:
        variable = root.children[0].value
        if variable is None:
            raise EvaluationError("El AST de asignación no contiene identificador")
        return variable, _evaluate_expression(root.children[2])
    return None, _evaluate_expression(root)


def _evaluate_expression(node: ASTNode) -> float:
    if node.symbol == "num":
        return float(node.value or "0")
    if node.symbol == "id":
        raise EvaluationError(
            f"No se puede evaluar el identificador {node.value!r} sin un entorno"
        )
    children = node.children
    if node.symbol in {"E", "T"} and len(children) == 3:
        left = _evaluate_expression(children[0])
        right = _evaluate_expression(children[2])
        operator = children[1].symbol
        operations = {
            "+": lambda: left + right,
            "-": lambda: left - right,
            "*": lambda: left * right,
            "/": lambda: left / right,
        }
        try:
            return operations[operator]()
        except ZeroDivisionError as error:
            raise DivisionByZeroError("No se puede dividir entre cero") from error
    if node.symbol == "F" and len(children) == 3:
        return _evaluate_expression(children[1])
    if len(children) == 1:
        return _evaluate_expression(children[0])
    raise EvaluationError(f"No se pudo evaluar el nodo {node.symbol}")
