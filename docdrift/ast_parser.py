"""AST parser for extracting Python code signatures, parameters, CLI flags, and types."""

import ast
import re
from pathlib import Path
from typing import Dict, List, Optional, Union

from docdrift.models import CodeSymbol, ParameterInfo


class ASTParser:
    """Extracts function, method, class, and CLI flag symbols using Python AST."""

    def parse_source(self, code: str, file_path: str = "<memory>") -> List[CodeSymbol]:
        """Parse source code string into CodeSymbol objects."""
        try:
            tree = ast.parse(code, filename=file_path)
        except SyntaxError:
            return []

        symbols: List[CodeSymbol] = []
        code_lines = code.splitlines()

        # 1. Extract functions and methods
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name.startswith("_") and not node.name.startswith("__"):
                    continue

                params: List[ParameterInfo] = []
                args = node.args

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

                start_l = max(0, node.lineno - 1)
                raw_sig = code_lines[start_l] if start_l < len(code_lines) else None
                end_l = getattr(node, "end_lineno", node.lineno)

                symbols.append(
                    CodeSymbol(
                        name=node.name,
                        symbol_type="function",
                        file_path=file_path,
                        line_number=node.lineno,
                        end_line_number=end_l,
                        parameters=params,
                        return_type=return_type,
                        docstring=docstring,
                        raw_source=raw_sig,
                    )
                )

        # 2. Extract CLI Flags (argparse add_argument or click option)
        cli_symbols = self._extract_cli_flags(tree, file_path, code_lines)
        symbols.extend(cli_symbols)

        return symbols

    def _extract_cli_flags(
        self,
        tree: ast.AST,
        file_path: str,
        code_lines: List[str],
    ) -> List[CodeSymbol]:
        """Extract CLI argument flags such as parser.add_argument('--timeout')."""
        cli_flags: List[CodeSymbol] = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func_name = ""
                if isinstance(node.func, ast.Attribute):
                    func_name = node.func.attr
                elif isinstance(node.func, ast.Name):
                    func_name = node.func.id

                if func_name in ("add_argument", "option"):
                    flag_names: List[str] = []
                    default_val = None
                    help_txt = None

                    for arg in node.args:
                        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                            if arg.value.startswith("-"):
                                flag_names.append(arg.value)

                    for kw in node.keywords:
                        if kw.arg == "default":
                            default_val = ast.unparse(kw.value)
                        elif kw.arg == "help" and isinstance(kw.value, ast.Constant):
                            help_txt = str(kw.value.value)

                    for flag in flag_names:
                        if flag.startswith("--"):
                            start_l = max(0, node.lineno - 1)
                            raw_line = code_lines[start_l] if start_l < len(code_lines) else None
                            end_l = getattr(node, "end_lineno", node.lineno)
                            cli_flags.append(
                                CodeSymbol(
                                    name=flag,
                                    symbol_type="cli_flag",
                                    file_path=file_path,
                                    line_number=node.lineno,
                                    end_line_number=end_l,
                                    parameters=[
                                        ParameterInfo(
                                            name=flag,
                                            default_value=default_val,
                                            is_cli_flag=True,
                                            help_text=help_txt,
                                        )
                                    ],
                                    docstring=help_txt,
                                    raw_source=raw_line,
                                )
                            )

        return cli_flags

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
            parts = py_file.parts
            if any(part in (".venv", "venv", "__pycache__", ".tox", "build", "dist") for part in parts):
                continue
            for sym in self.parse_file(py_file):
                symbols_map[sym.name] = sym

        return symbols_map
