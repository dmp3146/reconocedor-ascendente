from lexer.tokens import Token, TokenType


class LexerError(ValueError):
    def __init__(self, message: str, line: int, column: int):
        self.line = line
        self.column = column
        super().__init__(f"{message} en línea {line}, columna {column}")


class Lexer:
    _single_char_tokens = {
        "=": TokenType.ASSIGN,
        "+": TokenType.PLUS,
        "-": TokenType.MINUS,
        "*": TokenType.MULTIPLY,
        "/": TokenType.DIVIDE,
        "(": TokenType.LEFT_PAREN,
        ")": TokenType.RIGHT_PAREN,
    }

    def tokenize(self, source: str) -> list[Token]:
        tokens: list[Token] = []
        index = 0
        line = 1
        column = 1

        while index < len(source):
            char = source[index]
            if char.isspace():
                if char == "\n":
                    line += 1
                    column = 1
                else:
                    column += 1
                index += 1
                continue

            start_line, start_column = line, column
            if char.isalpha() or char == "_":
                start = index
                while index < len(source) and (
                    source[index].isalnum() or source[index] == "_"
                ):
                    index += 1
                    column += 1
                tokens.append(
                    Token(TokenType.IDENTIFIER, source[start:index], start_line, start_column)
                )
                continue

            if char.isdigit():
                start = index
                while index < len(source) and source[index].isdigit():
                    index += 1
                    column += 1
                if index < len(source) and source[index] == ".":
                    index += 1
                    column += 1
                    if index == len(source) or not source[index].isdigit():
                        raise LexerError(
                            "Un número decimal debe tener dígitos después del punto",
                            start_line,
                            start_column,
                        )
                    while index < len(source) and source[index].isdigit():
                        index += 1
                        column += 1
                tokens.append(
                    Token(TokenType.NUMBER, source[start:index], start_line, start_column)
                )
                continue

            token_type = self._single_char_tokens.get(char)
            if token_type is not None:
                tokens.append(Token(token_type, char, start_line, start_column))
                index += 1
                column += 1
                continue

            raise LexerError(f"Carácter no reconocido {char!r}", line, column)

        tokens.append(Token(TokenType.EOF, "", line, column))
        return tokens
