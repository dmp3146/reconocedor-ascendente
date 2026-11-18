from dataclasses import dataclass
from enum import Enum


class TokenType(str, Enum):
    IDENTIFIER = "id"
    NUMBER = "num"
    ASSIGN = "="
    PLUS = "+"
    MINUS = "-"
    MULTIPLY = "*"
    DIVIDE = "/"
    LEFT_PAREN = "("
    RIGHT_PAREN = ")"
    EOF = "$"


@dataclass(frozen=True)
class Token:
    type: TokenType
    lexeme: str
    line: int
    column: int

    @property
    def symbol(self) -> str:
        return self.type.value

    def __str__(self) -> str:
        return f"{self.type.value}({self.lexeme!r})@{self.line}:{self.column}"
