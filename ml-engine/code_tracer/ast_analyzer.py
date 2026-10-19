"""
Static AST Code Analyzer and Control Flow Graph (CFG) Builder.
Parses Python source code into AST and builds strongly-typed DiagramGraph objects
(using DiagramType.CODE_FLOW and DiagramType.CODE_CALL_GRAPH)
with exact bidirectional SourceLocation line mappings.
"""

import ast
from typing import List, Dict, Set, Tuple, Any, Optional
from collections import defaultdict

from ir.models import (
    DiagramGraph,
    DiagramNode,
    DiagramEdge,
    DiagramType,
    DiagramMetadata,
    SourceLocation,
    NodeShape,
    NodeStyle,
)


class AstCodeAnalyzer:
    """
    Statically analyzes Python code into Control Flow Graphs and Call Graphs.
    Attaches exact line numbers and column offsets to each node via SourceLocation.
    """

    @classmethod
    def build_cfg(cls, source_code: str, title: Optional[str] = None) -> DiagramGraph:
        """
        Parses source code and generates a Control Flow Graph (DiagramType.CODE_FLOW).
        Nodes represent basic blocks, statements, decisions, and loop headers.
        Edges represent sequential execution, true/false condition branches, and loop cycles.
        """
        tree = ast.parse(source_code)
        lines = source_code.splitlines()

        nodes: List[DiagramNode] = []
        edges: List[DiagramEdge] = []
        node_counter = 1
        edge_counter = 1

        def next_node_id() -> str:
            nonlocal node_counter
            nid = f"cfg_{node_counter}"
            node_counter += 1
            return nid

        def next_edge_id() -> str:
            nonlocal edge_counter
            eid = f"flow_{edge_counter}"
            edge_counter += 1
            return eid

        def extract_snippet(start_line: int, end_line: int) -> str:
            if 1 <= start_line <= len(lines):
                end_idx = min(end_line, len(lines))
                return "\n".join(lines[start_line - 1:end_idx]).strip()
            return ""

        # Entry node
        entry_id = next_node_id()
        nodes.append(DiagramNode(
            id=entry_id,
            label="Start",
            type="terminal",
            style=NodeStyle(shape=NodeShape.ROUNDED_RECTANGLE),
            source_location=SourceLocation(line_start=1, line_end=1, code_snippet="Start"),
        ))

        def process_block(stmts: List[ast.stmt], prev_id: str) -> str:
            curr_prev = prev_id
            for stmt in stmts:
                curr_prev = process_stmt(stmt, curr_prev)
            return curr_prev

        def process_stmt(stmt: ast.stmt, prev_id: str) -> str:
            nonlocal nodes, edges
            start_l = stmt.lineno
            end_l = getattr(stmt, "end_lineno", stmt.lineno)
            snippet = extract_snippet(start_l, end_l)

            if isinstance(stmt, ast.If):
                test_str = ast.unparse(stmt.test) if hasattr(ast, "unparse") else "condition"
                decision_id = next_node_id()
                nodes.append(DiagramNode(
                    id=decision_id,
                    label=f"if {test_str}",
                    type="decision",
                    style=NodeStyle(shape=NodeShape.DIAMOND),
                    source_location=SourceLocation(
                        line_start=start_l,
                        line_end=start_l,
                        col_start=stmt.col_offset,
                        code_snippet=f"if {test_str}",
                    ),
                ))
                edges.append(DiagramEdge(
                    id=next_edge_id(),
                    source=prev_id,
                    target=decision_id,
                    edge_type="flow",
                ))

                # True branch
                true_exit = process_block(stmt.body, decision_id)
                # False branch
                false_exit = process_block(stmt.orelse, decision_id) if stmt.orelse else decision_id

                # Join node
                join_id = next_node_id()
                nodes.append(DiagramNode(
                    id=join_id,
                    label="Merge",
                    type="junction",
                    style=NodeStyle(shape=NodeShape.CIRCLE),
                    source_location=SourceLocation(line_start=end_l, line_end=end_l, code_snippet="Merge"),
                ))

                edges.append(DiagramEdge(
                    id=next_edge_id(),
                    source=true_exit,
                    target=join_id,
                    label="True",
                    edge_type="branch_yes",
                ))
                edges.append(DiagramEdge(
                    id=next_edge_id(),
                    source=false_exit,
                    target=join_id,
                    label="False",
                    edge_type="branch_no",
                ))
                return join_id

            elif isinstance(stmt, (ast.For, ast.While)):
                if isinstance(stmt, ast.For):
                    header = f"for {ast.unparse(stmt.target)} in {ast.unparse(stmt.iter)}" if hasattr(ast, "unparse") else "for loop"
                else:
                    header = f"while {ast.unparse(stmt.test)}" if hasattr(ast, "unparse") else "while loop"

                loop_id = next_node_id()
                nodes.append(DiagramNode(
                    id=loop_id,
                    label=header,
                    type="loop",
                    style=NodeStyle(shape=NodeShape.HEXAGON),
                    source_location=SourceLocation(
                        line_start=start_l,
                        line_end=start_l,
                        col_start=stmt.col_offset,
                        code_snippet=header,
                    ),
                ))
                edges.append(DiagramEdge(
                    id=next_edge_id(),
                    source=prev_id,
                    target=loop_id,
                    edge_type="flow",
                ))

                # Loop body
                body_exit = process_block(stmt.body, loop_id)
                # Loop back-edge
                edges.append(DiagramEdge(
                    id=next_edge_id(),
                    source=body_exit,
                    target=loop_id,
                    label="repeat",
                    edge_type="loop_back",
                ))

                # Loop exit node
                exit_id = next_node_id()
                nodes.append(DiagramNode(
                    id=exit_id,
                    label="Exit Loop",
                    type="junction",
                    style=NodeStyle(shape=NodeShape.CIRCLE),
                    source_location=SourceLocation(line_start=end_l, line_end=end_l, code_snippet="Exit Loop"),
                ))
                edges.append(DiagramEdge(
                    id=next_edge_id(),
                    source=loop_id,
                    target=exit_id,
                    label="done",
                    edge_type="loop_exit",
                ))
                return exit_id

            elif isinstance(stmt, ast.FunctionDef):
                fn_id = next_node_id()
                fn_label = f"def {stmt.name}(...)"
                nodes.append(DiagramNode(
                    id=fn_id,
                    label=fn_label,
                    type="function",
                    style=NodeStyle(shape=NodeShape.ROUNDED_RECTANGLE),
                    source_location=SourceLocation(
                        line_start=start_l,
                        line_end=end_l,
                        col_start=stmt.col_offset,
                        symbol_name=stmt.name,
                        code_snippet=fn_label,
                    ),
                ))
                edges.append(DiagramEdge(
                    id=next_edge_id(),
                    source=prev_id,
                    target=fn_id,
                    edge_type="declaration",
                ))
                fn_exit = process_block(stmt.body, fn_id)
                return fn_exit

            elif isinstance(stmt, ast.Return):
                ret_val = ast.unparse(stmt.value) if stmt.value and hasattr(ast, "unparse") else "None"
                ret_id = next_node_id()
                nodes.append(DiagramNode(
                    id=ret_id,
                    label=f"return {ret_val}",
                    type="return",
                    style=NodeStyle(shape=NodeShape.PARALLELOGRAM),
                    source_location=SourceLocation(
                        line_start=start_l,
                        line_end=end_l,
                        col_start=stmt.col_offset,
                        code_snippet=f"return {ret_val}",
                    ),
                ))
                edges.append(DiagramEdge(
                    id=next_edge_id(),
                    source=prev_id,
                    target=ret_id,
                    edge_type="return",
                ))
                return ret_id

            else:
                # Standard statement (Assign, Expr, Call, etc.)
                stmt_str = snippet.split("\n")[0] if snippet else "stmt"
                if len(stmt_str) > 40:
                    stmt_str = stmt_str[:37] + "..."

                s_id = next_node_id()
                nodes.append(DiagramNode(
                    id=s_id,
                    label=stmt_str,
                    type="statement",
                    style=NodeStyle(shape=NodeShape.RECTANGLE),
                    source_location=SourceLocation(
                        line_start=start_l,
                        line_end=end_l,
                        col_start=stmt.col_offset,
                        code_snippet=snippet,
                    ),
                ))
                edges.append(DiagramEdge(
                    id=next_edge_id(),
                    source=prev_id,
                    target=s_id,
                    edge_type="flow",
                ))
                return s_id

        # Process all top-level statements
        last_exit = process_block(tree.body, entry_id)

        # End node
        end_id = next_node_id()
        nodes.append(DiagramNode(
            id=end_id,
            label="End",
            type="terminal",
            style=NodeStyle(shape=NodeShape.ROUNDED_RECTANGLE),
            source_location=SourceLocation(
                line_start=len(lines) or 1,
                line_end=len(lines) or 1,
                code_snippet="End",
            ),
        ))
        edges.append(DiagramEdge(
            id=next_edge_id(),
            source=last_exit,
            target=end_id,
            edge_type="flow",
        ))

        return DiagramGraph(
            id=f"cfg_{abs(hash(source_code)) % 10000:04d}",
            diagram_type=DiagramType.CODE_FLOW,
            version="2.0.0",
            nodes=nodes,
            edges=edges,
            metadata=DiagramMetadata(
                title=title or "Python Control Flow Graph",
                is_code_derived=True,
                source_language="python",
            ),
        )

    @classmethod
    def build_call_graph(cls, source_code: str, title: Optional[str] = None) -> DiagramGraph:
        """
        Extracts function definitions and caller-callee relationships
        into a Call Graph (DiagramType.CODE_CALL_GRAPH).
        """
        tree = ast.parse(source_code)
        func_nodes: Dict[str, ast.FunctionDef] = {}
        func_calls: Dict[str, Set[str]] = defaultdict(set)

        # Discover all functions
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                func_nodes[node.name] = node

        # Discover calls inside each function
        for fn_name, fn_ast in func_nodes.items():
            for child in ast.walk(fn_ast):
                if isinstance(child, ast.Call) and isinstance(child.func, ast.Name):
                    callee = child.func.id
                    if callee in func_nodes:
                        func_calls[fn_name].add(callee)

        # Build DiagramGraph
        nodes: List[DiagramNode] = []
        edges: List[DiagramEdge] = []

        for fn_name, fn_ast in sorted(func_nodes.items()):
            nodes.append(DiagramNode(
                id=f"fn_{fn_name}",
                label=f"{fn_name}()",
                type="function",
                style=NodeStyle(shape=NodeShape.ROUNDED_RECTANGLE),
                source_location=SourceLocation(
                    line_start=fn_ast.lineno,
                    line_end=getattr(fn_ast, "end_lineno", fn_ast.lineno),
                    symbol_name=fn_name,
                    code_snippet=f"def {fn_name}(...):",
                ),
            ))

        edge_counter = 1
        for caller, callees in sorted(func_calls.items()):
            for callee in sorted(callees):
                is_recursive = caller == callee
                edges.append(DiagramEdge(
                    id=f"call_{edge_counter}",
                    source=f"fn_{caller}",
                    target=f"fn_{callee}",
                    label="recursive call" if is_recursive else "calls",
                    edge_type="call",
                    directed=True,
                ))
                edge_counter += 1

        return DiagramGraph(
            id=f"callgraph_{abs(hash(source_code)) % 10000:04d}",
            diagram_type=DiagramType.CODE_CALL_GRAPH,
            version="2.0.0",
            nodes=nodes,
            edges=edges,
            metadata=DiagramMetadata(
                title=title or "Function Call Hierarchy",
                is_code_derived=True,
                source_language="python",
            ),
        )
