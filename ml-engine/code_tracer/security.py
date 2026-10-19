"""
AST Security Scanner and Sandboxing Safeguards for Code Execution.
Statically analyzes submitted Python snippets before execution to prevent
remote code execution, host filesystem access, network communication,
and sandbox escapes.
"""

import ast
from typing import List, Set, Tuple, Optional


class SecurityViolationError(Exception):
    """Raised when submitted code violates sandbox security constraints."""
    def __init__(self, message: str, line_number: Optional[int] = None, construct: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.line_number = line_number
        self.construct = construct


class AstSecurityScanner(ast.NodeVisitor):
    """
    Scans a Python Abstract Syntax Tree (AST) for prohibited operations.
    Rejects:
    - Dangerous imports (os, sys, subprocess, socket, shutil, ctypes, etc.)
    - Dangerous builtins (open, eval, exec, __import__, compile, input)
    - Dunder attribute exploitation (__subclasses__, __bases__, __globals__, etc.)
    - Asynchronous / coroutine constructs unsupported by simple educational tracer.
    """

    BANNED_MODULES: Set[str] = {
        "os", "sys", "subprocess", "socket", "shutil", "ctypes",
        "threading", "multiprocessing", "builtins", "importlib",
        "requests", "urllib", "http", "pickle", "shelve", "pty",
        "commands", "pdb", "tempfile", "pathlib", "gc", "posix",
        "nt", "signal", "inspect", "tokenize", "site", "pip",
        "venv", "platform", "winreg", "msvcrt", "conio", "ftplib",
        "poplib", "imaplib", "smtplib", "telnetlib", "ssl",
    }

    BANNED_CALLS: Set[str] = {
        "open", "eval", "exec", "compile", "__import__",
        "globals", "locals", "vars", "input", "help",
        "quit", "exit", "breakpoint", "memoryview",
    }

    BANNED_ATTRIBUTES: Set[str] = {
        "__subclasses__", "__bases__", "__mro__", "__globals__",
        "__code__", "__closure__", "__dict__", "__builtins__",
        "__import__", "__loader__", "__spec__",
    }

    def __init__(self):
        super().__init__()
        self.violations: List[Tuple[int, str, str]] = []

    def scan(self, source_code: str) -> List[Tuple[int, str, str]]:
        """
        Parses source code into AST and visits all nodes.
        Returns a list of (line_number, construct, reason) for any security violations.
        Raises SyntaxError if source code cannot be parsed.
        """
        self.violations = []
        tree = ast.parse(source_code)
        self.visit(tree)
        return self.violations

    def verify_or_raise(self, source_code: str):
        """
        Runs scan and raises SecurityViolationError on the first detected violation.
        """
        violations = self.scan(source_code)
        if violations:
            line_no, construct, reason = violations[0]
            raise SecurityViolationError(
                f"Security violation at line {line_no}: {reason} ('{construct}')",
                line_number=line_no,
                construct=construct,
            )

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            base_mod = alias.name.split(".")[0]
            if base_mod in self.BANNED_MODULES:
                self.violations.append((
                    node.lineno,
                    alias.name,
                    f"Import of forbidden module '{alias.name}' is prohibited for security."
                ))
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        if node.module:
            base_mod = node.module.split(".")[0]
            if base_mod in self.BANNED_MODULES:
                self.violations.append((
                    node.lineno,
                    node.module,
                    f"Import from forbidden module '{node.module}' is prohibited for security."
                ))
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        # Direct function calls: eval(), exec(), open()
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
            if func_name in self.BANNED_CALLS:
                self.violations.append((
                    node.lineno,
                    func_name,
                    f"Call to restricted built-in function '{func_name}()' is prohibited."
                ))
        # Method calls: obj.__subclasses__()
        elif isinstance(node.func, ast.Attribute):
            attr_name = node.func.attr
            if attr_name in self.BANNED_ATTRIBUTES:
                self.violations.append((
                    node.lineno,
                    attr_name,
                    f"Access or invocation of internal attribute '{attr_name}' is prohibited."
                ))
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute):
        if node.attr in self.BANNED_ATTRIBUTES:
            self.violations.append((
                node.lineno,
                node.attr,
                f"Access to restricted internal attribute '{node.attr}' is prohibited."
            ))
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self.violations.append((
            node.lineno,
            node.name,
            "Asynchronous functions (async def) are not supported by the tracer."
        ))
        self.generic_visit(node)

    def visit_Await(self, node: ast.Await):
        self.violations.append((
            node.lineno,
            "await",
            "Asynchronous expressions (await) are not supported by the tracer."
        ))
        self.generic_visit(node)
