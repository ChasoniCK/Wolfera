from __future__ import annotations

from typing import Any, Optional

from errors import InvalidSyntaxError
from lexer import Token, TokenType
from ast_nodes import (
    BinOpNode,
    BreakNode,
    CallNode,
    ContinueNode,
    DictNode,
    DoNode,
    DotGetNode,
    DotSetNode,
    ForInNode,
    ForNode,
    FuncDefNode,
    IfNode,
    ImportNode,
    IndexGetNode,
    IndexSetNode,
    ListNode,
    NamespaceNode,
    NumberNode,
    ReturnNode,
    StringNode,
    StructCreationNode,
    StructNode,
    SwitchNode,
    TryNode,
    UnaryOpNode,
    VarAccessNode,
    VarAssignNode,
    WhileNode,
)
# PARSE RESULT
#######################################


class ParseResult:
    def __init__(self):
        self.error: Optional[InvalidSyntaxError] = None
        self.node: Any = None
        self.last_registered_advance_count = 0
        self.advance_count = 0
        self.to_reverse_count = 0

    def register_advancement(self):
        self.last_registered_advance_count = 1
        self.advance_count += 1

    def register(self, res):
        self.last_registered_advance_count = res.advance_count
        self.advance_count += res.advance_count
        if res.error:
            self.error = res.error
        return res.node

    def try_register(self, res):
        if res.error:
            self.to_reverse_count = res.advance_count
            return None
        return self.register(res)

    def success(self, node):
        self.node = node
        return self

    def failure(self, error):
        if not self.error or self.last_registered_advance_count == 0:
            self.error = error
        return self

#######################################
# PARSER
#######################################


class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.tok_idx = -1
        dummy = ParseResult()
        self.advance(dummy)

    def advance(self, res: ParseResult) -> Optional[Token]:
        self.tok_idx += 1
        self.update_current_tok()
        res.register_advancement()
        return self.current_tok

    def reverse(self, amount=1):
        self.tok_idx -= amount
        self.update_current_tok()
        return self.current_tok

    def update_current_tok(self):
        if self.tok_idx >= 0 and self.tok_idx < len(self.tokens):
            self.current_tok = self.tokens[self.tok_idx]

    def parse(self):
        res = self.statements()
        if not res.error and self.current_tok.type != TokenType.EOF:
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start, self.current_tok.pos_end,
                "Token cannot appear after previous tokens"
            ))
        return res

    ###################################

    def statements(self):
        res = ParseResult()
        statements = []
        pos_start = self.current_tok.pos_start.copy()

        while self.current_tok.type == TokenType.NEWLINE:
            self.advance(res)

        if self.current_tok.type in (TokenType.EOF, TokenType.RCURLY):
            return res.success(ListNode(
                statements,
                pos_start,
                self.current_tok.pos_end.copy()
            ))

        statement = res.register(self.statement())
        if res.error:
            return res
        statements.append(statement)

        more_statements = True

        while True:
            newline_count = 0
            while self.current_tok.type == TokenType.NEWLINE:
                self.advance(res)
                newline_count += 1
            if newline_count == 0:
                more_statements = False

            if not more_statements:
                break
            statement = res.try_register(self.statement())
            if not statement:
                self.reverse(res.to_reverse_count)
                more_statements = False
                continue
            statements.append(statement)

        return res.success(ListNode(
            statements,
            pos_start,
            self.current_tok.pos_end.copy()
        ))

    def block(self):
        res = ParseResult()

        while self.current_tok.type == TokenType.NEWLINE:
            self.advance(res)

        while self.current_tok.type == TokenType.NEWLINE:
            self.advance(res)

        if self.current_tok.type != TokenType.LCURLY:
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start, self.current_tok.pos_end,
                "Expected '{'"
            ))

        self.advance(res)

        while self.current_tok.type == TokenType.NEWLINE:
            self.advance(res)

        statements = res.register(self.statements())
        if res.error:
            return res

        if self.current_tok.type != TokenType.RCURLY:
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start, self.current_tok.pos_end,
                "Expected '}'"
            ))

        self.advance(res)
        return res.success(statements)

    def statement(self):
        res = ParseResult()
        pos_start = self.current_tok.pos_start.copy()

        if self.current_tok.matches(TokenType.KEYWORD, 'return'):
            self.advance(res)

            expr = res.try_register(self.expr())
            if not expr:
                self.reverse(res.to_reverse_count)
            return res.success(ReturnNode(expr, pos_start, self.current_tok.pos_start.copy()))

        if self.current_tok.matches(TokenType.KEYWORD, 'continue'):
            self.advance(res)
            return res.success(ContinueNode(pos_start, self.current_tok.pos_start.copy()))

        if self.current_tok.matches(TokenType.KEYWORD, 'break'):
            self.advance(res)
            return res.success(BreakNode(pos_start, self.current_tok.pos_start.copy()))

        if self.current_tok.matches(TokenType.KEYWORD, 'import'):
            self.advance(res)

            if not self.current_tok.type == TokenType.STRING:
                return res.failure(InvalidSyntaxError(
                    self.current_tok.pos_start, self.current_tok.pos_end,
                    "Expected string"
                ))

            string = res.register(self.atom())
            return res.success(ImportNode(string, pos_start, self.current_tok.pos_start.copy()))

        if self.current_tok.matches(TokenType.KEYWORD, 'try'):
            self.advance(res)
            try_node = res.register(self.try_statement())
            return res.success(try_node)

        if self.current_tok.matches(TokenType.KEYWORD, 'switch'):
            self.advance(res)
            switch_node = res.register(self.switch_statement())
            return res.success(switch_node)

        if self.current_tok.matches(TokenType.KEYWORD, 'struct'):
            self.advance(res)
            struct_node = res.register(self.struct_def())
            return res.success(struct_node)

        expr = res.register(self.expr())
        if res.error:
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start, self.current_tok.pos_end,
                "Expected 'switch', 'return', 'continue', 'break', 'if', 'for', 'while', 'fun', 'namespace', int, float, identifier, '+', '-', '(', '[', '{' or 'not'"
            ))
        return res.success(expr)

    def expr(self):
        res = ParseResult()

        var_assign_node = res.try_register(self.assign_expr())
        if var_assign_node:
            return res.success(var_assign_node)
        else:
            self.reverse(res.to_reverse_count)

        if self.current_tok.matches(TokenType.KEYWORD, "const"):
            self.advance(res)

            if self.current_tok.type != TokenType.IDENTIFIER:
                return res.failure(InvalidSyntaxError(
                    self.current_tok.pos_start, self.current_tok.pos_end,
                    "Expected identifier"
                ))

            identifier = self.current_tok

            self.advance(res)

            if self.current_tok.type != TokenType.EQ:
                return res.failure(InvalidSyntaxError(
                    self.current_tok.pos_start, self.current_tok.pos_end,
                    "Expected '='"
                ))

            self.advance(res)

            assign_expr = res.register(self.expr())
            if res.error:
                return res

            return res.success(VarAssignNode(identifier, assign_expr, is_const=True))

        node = res.register(self.bin_op(
            self.comp_expr, ((TokenType.KEYWORD, 'and'), (TokenType.KEYWORD, 'or'))))

        if res.error:
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start, self.current_tok.pos_end,
                "Expected 'if', 'for', 'while', 'fun', 'namespace', int, float, identifier, '+', '-', '(', '[', '{' or 'not'"
            ))

        if self.current_tok.type == TokenType.EQ:
            return res.failure(InvalidSyntaxError(
                node.pos_start, node.pos_end,
                "Invalid assignment"
            ))

        return res.success(node)

    def assign_expr(self):
        res = ParseResult()
        pos_start = self.current_tok.pos_start

        if self.current_tok.type != TokenType.IDENTIFIER:
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start, self.current_tok.pos_end,
                "Expected 'if', 'for', 'while', 'fun', 'namespace', int, float, identifier, '+', '-', '(', '[', '{' or 'not'"
            ))

        var_name_tok = self.current_tok

        self.advance(res)

        if self.current_tok.type != TokenType.EQ:
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start, self.current_tok.pos_end,
                "Expected '='"
            ))

        self.advance(res)

        assign_expr = res.register(self.expr())
        if res.error:
            return res

        return res.success(VarAssignNode(var_name_tok, assign_expr))

    def comp_expr(self):
        res = ParseResult()

        if self.current_tok.matches(TokenType.KEYWORD, 'not'):
            op_tok = self.current_tok
            self.advance(res)

            node = res.register(self.comp_expr())
            if res.error:
                return res
            return res.success(UnaryOpNode(op_tok, node))

        node = res.register(self.bin_op(self.arith_expr, (TokenType.EE, TokenType.NE,
                            TokenType.LT, TokenType.GT, TokenType.LTE, TokenType.GTE)))

        if res.error:
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start, self.current_tok.pos_end,
                "Expected int, float, identifier, '+', '-', '(', '[', 'if', 'for', 'while', 'fun' or 'not'"
            ))

        return res.success(node)

    def arith_expr(self):
        return self.bin_op(self.term, (TokenType.PLUS, TokenType.MINUS))

    def term(self):
        return self.bin_op(self.factor, (TokenType.MUL, TokenType.DIV))

    def factor(self):
        res = ParseResult()
        tok = self.current_tok

        if tok.type in (TokenType.PLUS, TokenType.MINUS):
            self.advance(res)
            factor = res.register(self.factor())
            if res.error:
                return res
            return res.success(UnaryOpNode(tok, factor))

        return self.power()

    def power(self):
        return self.bin_op(self.call, (TokenType.POW, ), self.factor)

    def call(self):
        res = ParseResult()
        func = res.register(self.index())
        if res.error:
            return res

        if self.current_tok.type == TokenType.LPAREN:
            self.advance(res)
            arg_nodes = []

            if self.current_tok.type == TokenType.RPAREN:
                self.advance(res)
            else:
                arg_nodes.append(res.register(self.expr()))
                if res.error:
                    return res.failure(InvalidSyntaxError(
                        self.current_tok.pos_start, self.current_tok.pos_end,
                        "Expected ')', 'if', 'for', 'while', 'fun', 'namespace', int, float, identifier, '+', '-', '(', '[', '{' or 'not'"
                    ))

                while self.current_tok.type == TokenType.COMMA:
                    self.advance(res)

                    arg_nodes.append(res.register(self.expr()))
                    if res.error:
                        return res

                if self.current_tok.type != TokenType.RPAREN:
                    return res.failure(InvalidSyntaxError(
                        self.current_tok.pos_start, self.current_tok.pos_end,
                        f"Expected ',' or ')'"
                    ))

                self.advance(res)
            return res.success(CallNode(func, arg_nodes))
        return res.success(func)

    def index(self):  # TODO: allow stuff like list[0].upper()[3].(...)
        res = ParseResult()
        noun = res.register(self.dot())
        if res.error:
            return res

        node = noun
        while self.current_tok.type == TokenType.LSQUARE:
            self.advance(res)
            index = res.register(self.expr())
            if res.error:
                return res

            if self.current_tok.type != TokenType.RSQUARE:
                return res.failure(InvalidSyntaxError(
                    self.current_tok.pos_start, self.current_tok.pos_start,
                    "Expected ']'"
                ))

            node = IndexGetNode(node, index, node.pos_start,
                                self.current_tok.pos_end)
            self.advance(res)

        if self.current_tok.type == TokenType.EQ and isinstance(node, IndexGetNode):
            self.advance(res)

            value = res.register(self.expr())
            if res.error:
                return res

            node = IndexSetNode(node.indexee, node.index,
                                value, node.pos_start, self.current_tok.pos_end)

        return res.success(node)

    def dot(self):
        res = ParseResult()
        noun = res.register(self.atom())
        if res.error:
            return res

        node = noun
        while self.current_tok.type == TokenType.DOT:
            self.advance(res)

            if self.current_tok.type != TokenType.IDENTIFIER:
                return res.failure(InvalidSyntaxError(
                    self.current_tok.pos_start, self.current_tok.pos_start,
                    "Expected identifier"
                ))

            node = DotGetNode(node, self.current_tok,
                              node.pos_start, self.current_tok.pos_end)
            self.advance(res)

        if self.current_tok.type == TokenType.EQ and isinstance(node, DotGetNode):
            self.advance(res)

            value = res.register(self.expr())
            if res.error:
                return res

            node = DotSetNode(node.noun, node.verb, value,
                              node.pos_start, self.current_tok.pos_end)

        return res.success(node)

    def atom(self):
        res = ParseResult()
        tok = self.current_tok
        node = None

        if tok.type in (TokenType.INT, TokenType.FLOAT):
            self.advance(res)
            node = NumberNode(tok)

        elif tok.type == TokenType.STRING:
            self.advance(res)
            node = StringNode(tok)

        elif tok.type == TokenType.IDENTIFIER:
            self.advance(res)
            if self.current_tok.type == TokenType.LCURLY:
                struct_name = tok.value
                self.advance(res)
                if self.current_tok.type != TokenType.RCURLY:
                    return res.failure(InvalidSyntaxError(
                        self.current_tok.pos_start, self.current_tok.pos_end,
                        "Expected '}'"
                    ))
                self.advance(res)
                node = StructCreationNode(struct_name)
            else:
                node = VarAccessNode(tok)

        elif tok.type == TokenType.LPAREN:
            self.advance(res)
            expr = res.register(self.expr())
            if res.error:
                return res
            if self.current_tok.type == TokenType.RPAREN:
                self.advance(res)
                node = expr
            else:
                return res.failure(InvalidSyntaxError(
                    self.current_tok.pos_start, self.current_tok.pos_end,
                    "Expected ')'"
                ))

        elif tok.type == TokenType.LSQUARE:
            list_expr = res.register(self.list_expr())
            if res.error:
                return res
            node = list_expr

        elif tok.matches(TokenType.KEYWORD, 'if'):
            if_expr = res.register(self.if_expr())
            if res.error:
                return res
            node = if_expr

        elif tok.matches(TokenType.KEYWORD, 'for'):
            for_expr = res.register(self.for_expr())
            if res.error:
                return res
            node = for_expr

        elif tok.matches(TokenType.KEYWORD, 'while'):
            while_expr = res.register(self.while_expr())
            if res.error:
                return res
            node = while_expr

        elif tok.matches(TokenType.KEYWORD, 'fun'):
            func_def = res.register(self.func_def())
            if res.error:
                return res
            node = func_def

        elif tok.matches(TokenType.KEYWORD, 'namespace'):
            ns_expr = res.register(self.namespace_expr())
            if res.error:
                return res
            node = ns_expr

        elif tok.matches(TokenType.KEYWORD, 'do'):
            do_expr = res.register(self.do_expr())
            if res.error:
                return res
            node = do_expr

        elif tok.type == TokenType.LCURLY:
            dict_expr = res.register(self.dict_expr())
            if res.error:
                return res
            node = dict_expr

        if node is None:
            return res.failure(InvalidSyntaxError(
                tok.pos_start, tok.pos_end,
                "Expected int, float, identifier, '+', '-', '(', '[', 'if', 'for', 'while', 'fun'"
            ))

        return res.success(node)

    def list_expr(self):
        res = ParseResult()
        element_nodes = []
        pos_start = self.current_tok.pos_start.copy()

        if self.current_tok.type != TokenType.LSQUARE:
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start, self.current_tok.pos_end,
                f"Expected '['"
            ))

        self.advance(res)

        if self.current_tok.type == TokenType.RSQUARE:
            self.advance(res)
        else:
            element_nodes.append(res.register(self.expr()))
            if res.error:
                return res.failure(InvalidSyntaxError(
                    self.current_tok.pos_start, self.current_tok.pos_end,
                    "Expected ']', 'if', 'for', 'while', 'fun', 'namespace', int, float, identifier, '+', '-', '(', '[', '{' or 'not'"
                ))

            while self.current_tok.type == TokenType.COMMA:
                self.advance(res)

                element_nodes.append(res.register(self.expr()))
                if res.error:
                    return res

            if self.current_tok.type != TokenType.RSQUARE:
                return res.failure(InvalidSyntaxError(
                    self.current_tok.pos_start, self.current_tok.pos_end,
                    f"Expected ',' or ']'"
                ))

            self.advance(res)

        return res.success(ListNode(
            element_nodes,
            pos_start,
            self.current_tok.pos_end.copy()
        ))

    def dict_expr(self):
        res = ParseResult()
        pairs = []
        pos_start = self.current_tok.pos_start.copy()

        if self.current_tok.type != TokenType.LCURLY:
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start, self.current_tok.pos_end,
                "Expected '{'"
            ))

        self.advance(res)

        if self.current_tok.type == TokenType.RCURLY:
            self.advance(res)
        else:
            key = res.register(self.expr())
            if res.error:
                return res

            if self.current_tok.type != TokenType.COLON:
                return res.failure(InvalidSyntaxError(
                    self.current_tok.pos_start, self.current_tok.pos_end,
                    "Expected ':'"
                ))

            self.advance(res)

            value = res.register(self.expr())
            if res.error:
                return res

            pairs.append((key, value))

            while self.current_tok.type == TokenType.COMMA:
                self.advance(res)

                key = res.register(self.expr())
                if res.error:
                    return res

                if self.current_tok.type != TokenType.COLON:
                    return res.failure(InvalidSyntaxError(
                        self.current_tok.pos_start, self.current_tok.pos_end,
                        "Expected ':'"
                    ))

                self.advance(res)

                value = res.register(self.expr())
                if res.error:
                    return res

                pairs.append((key, value))

            if self.current_tok.type != TokenType.RCURLY:
                return res.failure(InvalidSyntaxError(
                    self.current_tok.pos_start, self.current_tok.pos_end,
                    "Expected ',' or '}'"
                ))

            self.advance(res)

        return res.success(DictNode(
            pairs,
            pos_start,
            self.current_tok.pos_end.copy()
        ))

    def if_expr(self):
        res = ParseResult()
        all_cases = res.register(self.if_expr_cases('if'))
        if res.error:
            return res
        cases, else_case = all_cases
        return res.success(IfNode(cases, else_case))

    def if_expr_b(self):
        return self.if_expr_cases('elif')

    def if_expr_c(self):
        res = ParseResult()
        else_case = None

        if self.current_tok.matches(TokenType.KEYWORD, 'else'):
            self.advance(res)
            statements = res.register(self.block())
            if res.error:
                return res
            else_case = (statements, True)

        return res.success(else_case)

    def if_expr_b_or_c(self):
        res = ParseResult()
        cases, else_case = [], None

        while self.current_tok.matches(TokenType.KEYWORD, 'elif'):
            self.advance(res)
            condition = res.register(self.expr())
            if res.error:
                return res
            body = res.register(self.block())
            if res.error:
                return res
            cases.append((condition, body, True))

        else_case = res.register(self.if_expr_c())
        if res.error:
            return res

        return res.success((cases, else_case))

    def if_expr_cases(self, case_keyword):
        res = ParseResult()
        cases = []
        else_case = None

        if not self.current_tok.matches(TokenType.KEYWORD, case_keyword):
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start, self.current_tok.pos_end,
                f"Expected '{case_keyword}'"
            ))

        self.advance(res)

        condition = res.register(self.expr())
        if res.error:
            return res

        body = res.register(self.block())
        if res.error:
            return res
        cases.append((condition, body, True))

        all_cases = res.register(self.if_expr_b_or_c())
        if res.error:
            return res
        new_cases, else_case = all_cases
        cases.extend(new_cases)

        return res.success((cases, else_case))

    def for_expr(self):
        res = ParseResult()
        pos_start = self.current_tok.pos_start.copy()
        iterable_node = None
        start_value = None
        end_value = None
        step_value = None

        if not self.current_tok.matches(TokenType.KEYWORD, 'for'):
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start, self.current_tok.pos_end,
                f"Expected 'for'"
            ))

        self.advance(res)

        if self.current_tok.type != TokenType.IDENTIFIER:
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start, self.current_tok.pos_end,
                f"Expected identifier"
            ))

        var_name = self.current_tok
        self.advance(res)

        is_for_in = False

        if self.current_tok.type != TokenType.EQ and not self.current_tok.matches(TokenType.KEYWORD, "in"):
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start, self.current_tok.pos_end,
                f"Expected '=' or 'in'"
            ))
        elif self.current_tok.matches(TokenType.KEYWORD, "in"):
            self.advance(res)
            is_for_in = True

            iterable_node = res.register(self.expr())
            if res.error:
                return res

        else:
            self.advance(res)

            start_value = res.register(self.expr())
            if res.error:
                return res

            if not self.current_tok.matches(TokenType.KEYWORD, 'to'):
                return res.failure(InvalidSyntaxError(
                    self.current_tok.pos_start, self.current_tok.pos_end,
                    f"Expected 'to'"
                ))

            self.advance(res)

            end_value = res.register(self.expr())
            if res.error:
                return res

            if self.current_tok.matches(TokenType.KEYWORD, 'step'):
                self.advance(res)

                step_value = res.register(self.expr())
                if res.error:
                    return res
            else:
                step_value = None

        body = res.register(self.block())
        if res.error:
            return res

        pos_end = body.pos_end

        if is_for_in:
            assert iterable_node is not None
            return res.success(ForInNode(var_name, iterable_node, body, pos_start, pos_end, True))
        assert start_value is not None
        assert end_value is not None
        return res.success(ForNode(var_name, start_value, end_value, step_value, body, True))

    def while_expr(self):
        res = ParseResult()

        if not self.current_tok.matches(TokenType.KEYWORD, 'while'):
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start, self.current_tok.pos_end,
                f"Expected 'while'"
            ))

        self.advance(res)

        condition = res.register(self.expr())
        if res.error:
            return res

        body = res.register(self.block())
        if res.error:
            return res

        return res.success(WhileNode(condition, body, True))

    def func_def(self):
        res = ParseResult()

        if not self.current_tok.matches(TokenType.KEYWORD, 'fun'):
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start, self.current_tok.pos_end,
                f"Expected 'fun'"
            ))

        self.advance(res)

        if self.current_tok.type == TokenType.IDENTIFIER:
            var_name_tok = self.current_tok
            self.advance(res)
            if self.current_tok.type != TokenType.LPAREN:
                return res.failure(InvalidSyntaxError(
                    self.current_tok.pos_start, self.current_tok.pos_end,
                    f"Expected '('"
                ))
        else:
            var_name_tok = None
            if self.current_tok.type != TokenType.LPAREN:
                return res.failure(InvalidSyntaxError(
                    self.current_tok.pos_start, self.current_tok.pos_end,
                    f"Expected identifier or '('"
                ))

        self.advance(res)
        arg_name_toks = []
        defaults = []
        dynamics = []
        hasOptionals = False

        if self.current_tok.type == TokenType.IDENTIFIER:
            pos_start = self.current_tok.pos_start.copy()
            pos_end = self.current_tok.pos_end.copy()
            arg_name_toks.append(self.current_tok)
            self.advance(res)

            if self.current_tok.type == TokenType.EQ:
                self.advance(res)
                default = res.register(self.expr())
                if res.error:
                    return res
                defaults.append(default)
                hasOptionals = True
            elif hasOptionals:
                return res.failure(InvalidSyntaxError(
                    pos_start, pos_end,
                    "Expected optional parameter."
                ))
            else:
                defaults.append(None)

            if self.current_tok.matches(TokenType.KEYWORD, 'from'):
                self.advance(res)
                dynamics.append(res.register(self.expr()))
                if res.error:
                    return res
            else:
                dynamics.append(None)

            while self.current_tok.type == TokenType.COMMA:
                self.advance(res)

                if self.current_tok.type != TokenType.IDENTIFIER:
                    return res.failure(InvalidSyntaxError(
                        self.current_tok.pos_start, self.current_tok.pos_end,
                        f"Expected identifier"
                    ))

                pos_start = self.current_tok.pos_start.copy()
                pos_end = self.current_tok.pos_end.copy()
                arg_name_toks.append(self.current_tok)
                self.advance(res)

                if self.current_tok.type == TokenType.EQ:
                    self.advance(res)
                    default = res.register(self.expr())
                    if res.error:
                        return res
                    defaults.append(default)
                    hasOptionals = True
                elif hasOptionals:
                    return res.failure(InvalidSyntaxError(
                        pos_start, pos_end,
                        "Expected optional parameter."
                    ))
                else:
                    defaults.append(None)

                if self.current_tok.matches(TokenType.KEYWORD, 'from'):
                    self.advance(res)
                    dynamics.append(res.register(self.expr()))
                    if res.error:
                        return res
                else:
                    dynamics.append(None)

            if self.current_tok.type != TokenType.RPAREN:
                return res.failure(InvalidSyntaxError(
                    self.current_tok.pos_start, self.current_tok.pos_end,
                    f"Expected ',', ')' or '='"
                ))
        else:
            if self.current_tok.type != TokenType.RPAREN:
                return res.failure(InvalidSyntaxError(
                    self.current_tok.pos_start, self.current_tok.pos_end,
                    f"Expected identifier or ')'"
                ))

        self.advance(res)

        if self.current_tok.type == TokenType.ARROW:
            self.advance(res)

            body = res.register(self.expr())
            if res.error:
                return res

            return res.success(FuncDefNode(
                var_name_tok,
                arg_name_toks,
                defaults,
                dynamics,
                body,
                True
            ))

        body = res.register(self.block())
        if res.error:
            return res

        return res.success(FuncDefNode(
            var_name_tok,
            arg_name_toks,
            defaults,
            dynamics,
            body,
            False
        ))

    def do_expr(self):
        res = ParseResult()
        pos_start = self.current_tok.pos_start.copy()

        self.advance(res)

        statements = res.register(self.block())
        if res.error:
            return res

        return res.success(DoNode(statements, pos_start, statements.pos_end))

    def try_statement(self):
        res = ParseResult()
        pos_start = self.current_tok.pos_start.copy()

        try_block = res.register(self.block())
        if res.error:
            return res

        if not self.current_tok.matches(TokenType.KEYWORD, 'catch'):
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start, self.current_tok.pos_end,
                "Expected 'catch'"
            ))

        self.advance(res)

        if not self.current_tok.matches(TokenType.KEYWORD, 'as'):
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start, self.current_tok.pos_end,
                "Expected 'as'"
            ))

        self.advance(res)

        if self.current_tok.type != TokenType.IDENTIFIER:
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start, self.current_tok.pos_end,
                "Expected identifier"
            ))

        exc_iden = self.current_tok.copy()
        self.advance(res)

        catch_block = res.register(self.block())
        if res.error:
            return res

        return res.success(TryNode(try_block, exc_iden, catch_block, pos_start, catch_block.pos_end))

    def switch_statement(self):
        res = ParseResult()
        pos_start = self.current_tok.pos_start

        condition = res.register(self.expr())
        if res.error:
            (res.error)
            return res

        if self.current_tok.type != TokenType.LCURLY:
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start, self.current_tok.pos_end,
                "Expected '{'"
            ))
        self.advance(res)

        while self.current_tok.type == TokenType.NEWLINE:
            self.advance(res)

        cases = []
        while self.current_tok.matches(TokenType.KEYWORD, "case"):
            self.advance(res)
            case = res.register(self.expr())
            if res.error:
                return res

            body = res.register(self.block())
            if res.error:
                return res

            cases.append((case, body))

            while self.current_tok.type == TokenType.NEWLINE:
                self.advance(res)

        else_case = None
        if self.current_tok.matches(TokenType.KEYWORD, "else"):
            self.advance(res)
            else_case = res.register(self.block())
            if res.error:
                return res

        if self.current_tok.type != TokenType.RCURLY:
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start, self.current_tok.pos_end,
                "Expected '}'"
            ))

        pos_end = self.current_tok.pos_end
        self.advance(res)

        node = SwitchNode(condition, cases, else_case, pos_start, pos_end)
        return res.success(node)

    def struct_def(self):
        res = ParseResult()

        if self.current_tok.type != TokenType.IDENTIFIER:
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start, self.current_tok.pos_end,
                "Expected identifier"
            ))

        pos_start = self.current_tok.pos_start
        name = self.current_tok.value
        self.advance(res)

        while self.current_tok.type == TokenType.NEWLINE:
            self.advance(res)

        if self.current_tok.type != TokenType.LCURLY:
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start, self.current_tok.pos_end,
                "Expected '{'"
            ))

        self.advance(res)

        while self.current_tok.type == TokenType.NEWLINE:
            self.advance(res)

        fields = []
        while self.current_tok.type == TokenType.IDENTIFIER:
            fields.append(self.current_tok.value)
            self.advance(res)
            if self.current_tok.type == TokenType.COMMA:
                self.advance(res)
            while self.current_tok.type == TokenType.NEWLINE:
                self.advance(res)

        if self.current_tok.type != TokenType.RCURLY:
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start, self.current_tok.pos_end,
                "Expected '}' or identifier"
            ))

        pos_end = self.current_tok.pos_end
        self.advance(res)
        return res.success(StructNode(name=name, fields=fields, pos_start=pos_start, pos_end=pos_end))

    def namespace_expr(self):
        res = ParseResult()
        pos_start = self.current_tok.pos_start.copy()

        self.advance(res)

        statements = res.register(self.block())
        if res.error:
            return res

        return res.success(DoNode(statements, pos_start, statements.pos_end))

    ###################################

    def bin_op(self, func_a, ops, func_b=None):
        if func_b == None:
            func_b = func_a

        res = ParseResult()
        left = res.register(func_a())
        if res.error:
            return res

        while self.current_tok.type in ops or (self.current_tok.type, self.current_tok.value) in ops:
            op_tok = self.current_tok
            self.advance(res)
            right = res.register(func_b())
            if res.error:
                return res
            left = BinOpNode(left, op_tok, right)

        return res.success(left)

#######################################
