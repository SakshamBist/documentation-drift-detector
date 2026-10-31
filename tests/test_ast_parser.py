"""Unit tests for AST Parser."""

from docdrift.ast_parser import ASTParser


def test_parse_simple_function():
    code = """
def calculate_metrics(data: list, window: int = 10, verbose: bool = False) -> float:
    '''Calculates moving average metrics.'''
    return 42.0
"""
    parser = ASTParser()
    symbols = parser.parse_source(code)

    assert len(symbols) == 1
    sym = symbols[0]
    assert sym.name == "calculate_metrics"
    assert sym.return_type == "float"
    assert sym.docstring == "Calculates moving average metrics."

    param_names = sym.param_names()
    assert param_names == ["data", "window", "verbose"]

    assert sym.parameters[1].name == "window"
    assert sym.parameters[1].default_value == "10"
    assert sym.parameters[1].type_annotation == "int"


def test_ignore_private_functions():
    code = """
def public_api():
    pass

def _private_helper():
    pass
"""
    parser = ASTParser()
    symbols = parser.parse_source(code)

    assert len(symbols) == 1
    assert symbols[0].name == "public_api"
