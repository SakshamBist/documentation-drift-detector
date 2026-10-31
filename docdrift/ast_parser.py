"""AST parser for extracting Python code signatures, parameters, and types."""

import ast
from pathlib import Path
from typing import Dict, List, Optional, Union

from docdrift.models import CodeSymbol, ParameterInfo


class ASTParser:
    """Extracts function, method, and class symbols using Python AST."""

    def parse_source(self, code: str, file_path: str = "<memory>") -> List[CodeSymbol]:
        """Parse source code string into CodeSymbol objects."""
        try:
            tree = ast.parse(code, filename=file_path)
        except SyntaxError:
            return []

        symbols: List[CodeSymbol] = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Ignore private internal functions unless explicitly documented
                if node.name.startswith("_") and not node.name.startswith("__"):
                    continue

                params: List[ParameterInfo] = []
                args = node.args

                # Calculate offset for default values
                num_defaults = len(args.defaults)
                num_args = len(args.posonlyargs) + len(args.args)
                default_offset = num_args - num_defaults

                all_args = args.posonlyargs + args.args
                for idx, arg in enumerate(all_args):
                    param_name = arg.arg
                    type_ann = ast.unparse(arg.annotation) if arg.annotation else None

                    default_val = None
                    default_idx = idx - default_offset
                    if default_idx >= 0 and default_idx < len(args.defaults):
                        default_val = ast.unparse(args.defaults[default_idx])

                    params.append(
                        ParameterInfo(
                            name=param_name,
                            type_annotation=type_ann,
                            default_value=default_val,
                        )
                    )

                # Kwonly args
                for idx, arg in enumerate(args.kwonlyargs):
                    type_ann = ast.unparse(arg.annotation) if arg.annotation else None
                    default_val = None
                    if idx < len(args.kw_defaults) and args.kw_defaults[idx]:
                        default_val = ast.unparse(args.kw_defaults[idx])
                    params.append(
                        ParameterInfo(
                            name=arg.arg,
                            type_annotation=type_ann,
                            default_value=default_val,
                        )
                    )

                return_type = ast.unparse(node.returns) if node.returns else None
                docstring = ast.get_docstring(node)

                symbols.append(
                    CodeSymbol(
                        name=node.name,
                        symbol_type="function",
                        file_path=file_path,
                        line_number=node.lineno,
                        parameters=params,
                        return_type=return_type,
                        docstring=docstring,
                    )
                )

        return symbols

    def parse_file(self, file_path: Union[str, Path]) -> List[CodeSymbol]:
        """Parse a single Python file."""
        p = Path(file_path)
        if not p.is_file() or p.suffix != ".py":
            return []

        try:
            content = p.read_text(encoding="utf-8", errors="ignore")
            return self.parse_source(content, file_path=str(p))
        except Exception:
            return []

    def parse_directory(self, dir_path: Union[str, Path]) -> Dict[str, CodeSymbol]:
        """Parse all Python files in a directory recursively into a name -> symbol map."""
        p = Path(dir_path)
        symbols_map: Dict[str, CodeSymbol] = {}

        if p.is_file():
            for sym in self.parse_file(p):
                symbols_map[sym.name] = sym
            return symbols_map

        for py_file in p.rglob("*.py"):
            # Skip virtualenvs, tests, caches
            parts = py_file.parts
            if any(part in (".venv", "venv", "__pycache__", ".tox", "build", "dist") for part in parts):
                continue
            for sym in self.parse_file(py_file):
                symbols_map[sym.name] = sym

        return symbols_map
