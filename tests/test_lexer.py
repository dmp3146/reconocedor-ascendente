import pytest

from lexer.lexer import Lexer, LexerError
from lexer.tokens import TokenType


def test_lexer_recognizes_every_token_and_positions():
    tokens = Lexer().tokenize("var_1 = 12.50 + (3 - 4) * 2 / 1")
    assert [token.type for token in tokens] == [
        TokenType.IDENTIFIER, TokenType.ASSIGN, TokenType.NUMBER,
        TokenType.PLUS, TokenType.LEFT_PAREN, TokenType.NUMBER,
        TokenType.MINUS, TokenType.NUMBER, TokenType.RIGHT_PAREN,
        TokenType.MULTIPLY, TokenType.NUMBER, TokenType.DIVIDE,
        TokenType.NUMBER, TokenType.EOF,
    ]
    assert (tokens[0].line, tokens[0].column) == (1, 1)
    assert tokens[-1].symbol == "$"


@pytest.mark.parametrize("source", ["1.", "12.a", "@", "x # 2"])
def test_lexer_reports_invalid_characters_or_numbers(source):
    with pytest.raises(LexerError):
        Lexer().tokenize(source)


def test_lexer_tracks_lines():
    token = Lexer().tokenize("1\n  x")
    assert token[1].line == 2
    assert token[1].column == 3
