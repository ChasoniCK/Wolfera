from __future__ import annotations

import argparse
import os
import sys

from ast_nodes import (
    BinOpNode,
    CallNode,
    DoNode,
    ForInNode,
    ForNode,
    FuncDefNode,
    IfNode,
    ListNode,
    NumberNode,
    ReturnNode,
    StringNode,
    SwitchNode,
    TryNode,
    UnaryOpNode,
    VarAccessNode,
    VarAssignNode,
    WhileNode,
)
from errors import Error
from interpreter import global_symbol_table, run
from lexer import Lexer, TokenType
from parser import Parser


TOKEN_SYMBOLS = {
    TokenType.PLUS: "+",
    TokenType.MINUS: "-",
    TokenType.MUL: "*",
    TokenType.DIV: "/",
    TokenType.MOD: "%",
    TokenType.POW: "^",
    TokenType.EE: "==",
    TokenType.NE: "!=",
    TokenType.LT: "<",
    TokenType.GT: ">",
    TokenType.LTE: "<=",
    TokenType.GTE: ">=",
}


def format_token(token) -> str:
    if token.type in (TokenType.INT, TokenType.FLOAT):
        return f"NUMBER({token.value})"
    if token.type == TokenType.STRING:
        return f"STRING({token.value})"
    if token.type == TokenType.IDENTIFIER:
        return f"IDENTIFIER({token.value})"
    if token.type == TokenType.KEYWORD:
        return str(token.value)
    return token.type.name


def op_to_text(op_tok) -> str:
    if op_tok.type == TokenType.KEYWORD:
        return str(op_tok.value)
    return TOKEN_SYMBOLS.get(op_tok.type, op_tok.type.name) or op_tok.type.name


def node_label(node) -> str:
    if isinstance(node, BinOpNode):
        return f"BinaryOp({op_to_text(node.op_tok)})"
    if isinstance(node, UnaryOpNode):
        return f"UnaryOp({op_to_text(node.op_tok)})"
    if isinstance(node, NumberNode):
        return f"Number({node.tok.value})"
    if isinstance(node, StringNode):
        return f"String({node.tok.value})"
    if isinstance(node, VarAccessNode):
        return f"VarAccess({node.var_name_tok.value})"
    if isinstance(node, VarAssignNode):
        return f"VarAssign({node.var_name_tok.value})"
    if isinstance(node, ListNode):
        return "List"
    if isinstance(node, CallNode):
        return "Call"
    if isinstance(node, FuncDefNode):
        return "FuncDef"
    if isinstance(node, IfNode):
        return "If"
    if isinstance(node, ForNode):
        return "For"
    if isinstance(node, ForInNode):
        return "ForIn"
    if isinstance(node, WhileNode):
        return "While"
    if isinstance(node, ReturnNode):
        return "Return"
    if isinstance(node, DoNode):
        return "Do"
    if isinstance(node, TryNode):
        return "Try"
    if isinstance(node, SwitchNode):
        return "Switch"
    return type(node).__name__


def node_children(node):
    if isinstance(node, BinOpNode):
        return [node.left_node, node.right_node]
    if isinstance(node, UnaryOpNode):
        return [node.node]
    if isinstance(node, ListNode):
        return list(node.element_nodes)
    if isinstance(node, VarAssignNode):
        return [node.value_node]
    if isinstance(node, CallNode):
        return [node.node_to_call] + list(node.arg_nodes)
    if isinstance(node, FuncDefNode):
        return list(node.arg_name_toks) + [node.body_node]
    if isinstance(node, IfNode):
        children = []
        for condition, expr, _ in node.cases:
            children.extend([condition, expr])
        if node.else_case:
            children.append(node.else_case[0])
        return children
    if isinstance(node, ForNode):
        return [
            node.start_value_node,
            node.end_value_node,
            node.step_value_node,
            node.body_node,
        ]
    if isinstance(node, ForInNode):
        return [node.iterable_node, node.body_node]
    if isinstance(node, WhileNode):
        return [node.condition_node, node.body_node]
    if isinstance(node, ReturnNode) and node.node_to_return:
        return [node.node_to_return]
    if isinstance(node, DoNode):
        return [node.statements]
    if isinstance(node, TryNode):
        return [node.try_block, node.catch_block]
    if isinstance(node, SwitchNode):
        children = [node.condition]
        for cond, body in node.cases:
            children.extend([cond, body])
        if node.else_case:
            children.append(node.else_case)
        return children
    return []


def build_tree_lines(node, prefix="", is_last=True, is_root=True):
    label = node_label(node)
    if is_root:
        lines = [label]
    else:
        connector = "└── " if is_last else "├── "
        lines = [prefix + connector + label]

    children = node_children(node)
    if not children:
        return lines

    child_prefix = "" if is_root else prefix + ("    " if is_last else "│   ")
    for idx, child in enumerate(children):
        last = idx == len(children) - 1
        lines.extend(build_tree_lines(child, child_prefix, last, is_root=False))
    return lines


def unwrap_single_statement(ast_node):
    if isinstance(ast_node, ListNode) and len(ast_node.element_nodes) == 1:
        return ast_node.element_nodes[0]
    return ast_node


def read_source(source: str) -> tuple[str, str]:
    if os.path.isfile(source):
        with open(source, "r") as f:
            return f.read(), source

    return source, "<cmd>"


def print_error(error: Error):
    print(error.as_string(), file=sys.stderr)


def handle_tokens(text: str, filename: str):
    lexer = Lexer(filename, text)
    tokens, error = lexer.make_tokens()
    if error:
        print_error(error)
        return 1
    for tok in tokens:
        if tok.type == TokenType.NEWLINE:
            continue
        print(format_token(tok))
    return 0


def handle_ast(text: str, filename: str):
    lexer = Lexer(filename, text)
    tokens, error = lexer.make_tokens()
    if error:
        print_error(error)
        return 1

    parser = Parser(tokens)
    ast = parser.parse()
    if ast.error:
        print_error(ast.error)
        return 1

    node = unwrap_single_statement(ast.node)
    for line in build_tree_lines(node):
        print(line)
    return 0


def run_code(text: str, filename: str, argv: list[str]):
    result, error = run(filename, text, argv=argv)
    if error:
        print_error(error)
        return 1
    return 0


def repl():
    while True:
        try:
            text = input('myopl++ > ')
        except EOFError:
            break
        if text.strip() == "":
            continue
        result, error = run('<stdin>', text)
        if error:
            print_error(error)
        elif result:
            real_result = result.elements[0] if hasattr(result, "elements") and len(result.elements) == 1 else result
            print(repr(real_result))
            global_symbol_table.set("_", real_result)


def main():
    parser = argparse.ArgumentParser(prog="main.py")
    parser.add_argument("source", nargs="?", help="Source code string or path to file")
    parser.add_argument("--ast", action="store_true", help="Print the AST")
    parser.add_argument("--tokens", action="store_true", help="Print tokens")
    args, remainder = parser.parse_known_args()

    if args.source is None:
        repl()
        return

    text, filename = read_source(args.source)

    if args.tokens:
        sys.exit(handle_tokens(text, filename))
    if args.ast:
        sys.exit(handle_ast(text, filename))

    argv = remainder
    if argv and argv[0] == "--":
        argv = argv[1:]
    sys.exit(run_code(text, filename, argv))


if __name__ == "__main__":
    main()
