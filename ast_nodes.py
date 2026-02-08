from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Tuple

from lexer import Position, Token


class NumberNode:
    def __init__(self, tok):
        self.tok = tok

        self.pos_start = self.tok.pos_start
        self.pos_end = self.tok.pos_end

    def __repr__(self):
        return f'{self.tok}'


class StringNode:
    def __init__(self, tok):
        self.tok = tok

        self.pos_start = self.tok.pos_start
        self.pos_end = self.tok.pos_end

    def __repr__(self):
        return f'{self.tok}'


class FStringNode:
    def __init__(self, tok, arg_nodes=None):
        self.tok = tok
        self.arg_nodes = arg_nodes or []
        self.pos_start = self.tok.pos_start
        self.pos_end = self.tok.pos_end

    def __repr__(self):
        if self.arg_nodes:
            return f'F{self.tok}({self.arg_nodes!r})'
        return f'F{self.tok}'

class ListNode:
    def __init__(self, element_nodes, pos_start, pos_end):
        self.element_nodes = element_nodes

        self.pos_start = pos_start
        self.pos_end = pos_end


class VarAccessNode:
    def __init__(self, var_name_tok):
        self.var_name_tok = var_name_tok

        self.pos_start = self.var_name_tok.pos_start
        self.pos_end = self.var_name_tok.pos_end


class VarAssignNode:
    def __init__(self, var_name_tok, value_node, is_const=False):
        self.var_name_tok = var_name_tok
        self.value_node = value_node
        self.is_const = is_const

        self.pos_start = self.var_name_tok.pos_start
        self.pos_end = self.value_node.pos_end

    def __repr__(self):
        const = "CONST " if self.is_const else ""
        return f"({const}{self.var_name_tok} = {self.value_node!r})"


class BinOpNode:
    def __init__(self, left_node, op_tok, right_node):
        self.left_node = left_node
        self.op_tok = op_tok
        self.right_node = right_node

        self.pos_start = self.left_node.pos_start
        self.pos_end = self.right_node.pos_end

    def __repr__(self):
        return f'({self.left_node}, {self.op_tok}, {self.right_node})'


class UnaryOpNode:
    def __init__(self, op_tok, node):
        self.op_tok = op_tok
        self.node = node

        self.pos_start = self.op_tok.pos_start
        self.pos_end = node.pos_end

    def __repr__(self):
        return f'({self.op_tok}, {self.node})'


class IfNode:
    def __init__(self, cases, else_case):
        self.cases = cases
        self.else_case = else_case

        self.pos_start = self.cases[0][0].pos_start
        self.pos_end = (
            self.else_case or self.cases[len(self.cases) - 1])[0].pos_end


class ForNode:
    def __init__(self, var_name_tok, start_value_node, end_value_node, step_value_node, body_node, should_return_null):
        self.var_name_tok = var_name_tok
        self.start_value_node = start_value_node
        self.end_value_node = end_value_node
        self.step_value_node = step_value_node
        self.body_node = body_node
        self.should_return_null = should_return_null

        self.pos_start = self.var_name_tok.pos_start
        self.pos_end = self.body_node.pos_end


class WhileNode:
    def __init__(self, condition_node, body_node, should_return_null):
        self.condition_node = condition_node
        self.body_node = body_node
        self.should_return_null = should_return_null

        self.pos_start = self.condition_node.pos_start
        self.pos_end = self.body_node.pos_end


class FuncDefNode:
    def __init__(self, var_name_tok, arg_name_toks, defaults, dynamics, body_node, should_auto_return):
        self.var_name_tok = var_name_tok
        self.arg_name_toks = arg_name_toks
        self.defaults = defaults
        self.dynamics = dynamics
        self.body_node = body_node
        self.should_auto_return = should_auto_return

        if self.var_name_tok:
            self.pos_start = self.var_name_tok.pos_start
        elif len(self.arg_name_toks) > 0:
            self.pos_start = self.arg_name_toks[0].pos_start
        else:
            self.pos_start = self.body_node.pos_start

        self.pos_end = self.body_node.pos_end


class CallNode:
    def __init__(self, node_to_call, arg_nodes):
        self.node_to_call = node_to_call
        self.arg_nodes = arg_nodes

        self.pos_start = self.node_to_call.pos_start

        if len(self.arg_nodes) > 0:
            self.pos_end = self.arg_nodes[len(self.arg_nodes) - 1].pos_end
        else:
            self.pos_end = self.node_to_call.pos_end


class ReturnNode:
    def __init__(self, node_to_return, pos_start, pos_end):
        self.node_to_return = node_to_return

        self.pos_start = pos_start
        self.pos_end = pos_end


class ContinueNode:
    def __init__(self, pos_start, pos_end):
        self.pos_start = pos_start
        self.pos_end = pos_end


class BreakNode:
    def __init__(self, pos_start, pos_end):
        self.pos_start = pos_start
        self.pos_end = pos_end


@dataclass
class ImportNode:
    module_path: Any
    pos_start: Position
    pos_end: Position

    def __repr__(self) -> str:
        return f"IMPORT {self.module_path!r}"


@dataclass
class FromImportNode:
    module_path: list[str]
    names: list[Token]
    pos_start: Position
    pos_end: Position

    def __repr__(self) -> str:
        names = ", ".join([str(name.value) for name in self.names])
        return f"FROM {'.'.join(self.module_path)} IMPORT {{{names}}}"


@dataclass
class DoNode:
    statements: ListNode
    pos_start: Position
    pos_end: Position

    def __repr__(self) -> str:
        return f'(DO {self.statements!r} END)'


@dataclass
class TryNode:
    try_block: ListNode
    exc_iden: Token
    catch_block: Any
    pos_start: Position
    pos_end: Position

    def __repr__(self) -> str:
        return f'(TRY {self.try_block!r} CATCH AS {self.exc_iden!r} THEN {self.catch_block!r})'


@dataclass
class ForInNode:
    var_name_tok: Token
    iterable_node: Any
    body_node: Any
    pos_start: Position
    pos_end: Position
    should_return_null: bool

    def __repr__(self) -> str:
        return f"(FOR {self.var_name_tok} IN {self.iterable_node!r} THEN {self.body_node!r})"


@dataclass
class IndexGetNode:
    indexee: Any
    index: Any
    pos_start: Position
    pos_end: Position

    def __repr__(self):
        return f"({self.indexee!r}[{self.index!r}])"


@dataclass
class IndexSetNode:
    indexee: Any
    index: Any
    value: Any
    pos_start: Position
    pos_end: Position

    def __repr__(self):
        return f"({self.indexee!r}[{self.index!r}]={self.value!r})"


@dataclass
class DictNode:
    pairs: list[tuple[Any, Any]]
    pos_start: Position
    pos_end: Position

    def __repr__(self):
        result = "({"
        for key, value in self.pairs:
            result += f"{key!r}: {value!r}"
        return result + "})"


INDENTATION = 4


@dataclass
class SwitchNode:
    condition: Any
    cases: list[Tuple[Any, ListNode]]
    else_case: Optional[ListNode]
    pos_start: Position
    pos_end: Position

    def __repr__(self):
        return f"(SWITCH {self.condition!r}\n " + (" " * INDENTATION) + ("\n " + " " * INDENTATION).join(
            f"CASE {case_cond!r}\n " + (" " * INDENTATION * 2) + f"{case_body!r}" for case_cond, case_body in list(self.cases)
        ) + "\n " + (" " * INDENTATION) + "ELSE\n" + (" " * INDENTATION * 2) + f"{self.else_case!r})"


@dataclass
class DotGetNode:
    noun: Any
    verb: Token
    pos_start: Position
    pos_end: Position

    def __repr__(self):
        return f"({self.noun!r}.{self.verb.value})"


@dataclass
class DotSetNode:
    noun: Any
    verb: Token
    value: Any
    pos_start: Position
    pos_end: Position

    def __repr__(self):
        return f"({self.noun!r}.{self.verb.value}={self.value!r})"


@dataclass
class NamespaceNode:
    name: Optional[Token]
    body: Any
    pos_start: Position
    pos_end: Position

    def __repr__(self):
        return f"""(NAMESPACE {
      self.name.value if self.name is not None
      else ""
    }\n{self.body!r}\nEND)"""


@dataclass
class StructNode:
    name: str
    fields: list[str]
    pos_start: Position
    pos_end: Position

    def __repr__(self):
        return f"STRUCT {self.name}: {', '.join(self.fields)}"


@dataclass
class StructCreationNode:
    name: str
    pos_start: Optional[Position] = None
    pos_end: Optional[Position] = None

    def __repr__(self):
        return f"{self.name}{{}}"
