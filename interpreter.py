from __future__ import annotations

import importlib.util
import math
import os
import sys
import time
from typing import Any, Callable, ClassVar, Optional, Protocol, cast

from ast_nodes import ListNode, StringNode
from errors import RTError, TryError
from lexer import Lexer, Position, TokenType
from parser import Parser

#######################################
# OPEN FILES (so they don't get automatically closed by GC)
#######################################

files = {}
MODULE_CACHE = {}

#######################################
# CONSTANTS
#######################################

IMPORT_PATH_NAME = ".path"
if not os.path.isfile(IMPORT_PATH_NAME):
    IMPORT_PATHS = [".", os.getcwd() + "/std"]
    with open(IMPORT_PATH_NAME, "w") as f:
        f.write("\n".join(IMPORT_PATHS))
else:
    with open(IMPORT_PATH_NAME, "r") as f:
        IMPORT_PATHS = [line.strip() for line in f.readlines() if line.strip()]

#######################################
# VALUES (BASE)
#######################################

ValueResult = tuple[Optional["Value"], Optional[RTError]]


class Value:
    def __init__(self):
        self.set_pos()
        self.set_context()

    def set_pos(self, pos_start=None, pos_end=None) -> "Value":
        self.pos_start = pos_start
        self.pos_end = pos_end
        return self

    def set_context(self, context=None) -> "Value":
        self.context = context
        return self

    def added_to(self, other: "Value") -> ValueResult:
        return None, self.illegal_operation(other)

    def subbed_by(self, other: "Value") -> ValueResult:
        return None, self.illegal_operation(other)

    def multed_by(self, other: "Value") -> ValueResult:
        return None, self.illegal_operation(other)

    def dived_by(self, other: "Value") -> ValueResult:
        return None, self.illegal_operation(other)

    def modded_by(self, other: "Value") -> ValueResult:
        return None, self.illegal_operation(other)

    def powed_by(self, other: "Value") -> ValueResult:
        return None, self.illegal_operation(other)

    def get_comparison_eq(self, other: "Value") -> ValueResult:
        return None, self.illegal_operation(other)

    def get_comparison_ne(self, other: "Value") -> ValueResult:
        return None, self.illegal_operation(other)

    def get_comparison_lt(self, other: "Value") -> ValueResult:
        return None, self.illegal_operation(other)

    def get_comparison_gt(self, other: "Value") -> ValueResult:
        return None, self.illegal_operation(other)

    def get_comparison_lte(self, other: "Value") -> ValueResult:
        return None, self.illegal_operation(other)

    def get_comparison_gte(self, other: "Value") -> ValueResult:
        return None, self.illegal_operation(other)

    def anded_by(self, other: "Value") -> ValueResult:
        return None, self.illegal_operation(other)

    def ored_by(self, other: "Value") -> ValueResult:
        return None, self.illegal_operation(other)

    def notted(self) -> ValueResult:
        return None, self.illegal_operation()

    def iter(self) -> "Iterator":
        return Iterator(self.gen)

    def gen(self):
        yield RTResult().failure(self.illegal_operation())

    def get_index(self, index: "Value") -> ValueResult:
        return None, self.illegal_operation(index)

    def set_index(self, index: "Value", value: "Value") -> ValueResult:
        return None, self.illegal_operation(index, value)

    def execute(self, args: list["Value"]) -> "RTResult":
        return RTResult().failure(self.illegal_operation())

    def get_dot(self, verb: str) -> tuple[Optional[Any], Optional[RTError]]:
        t = type(self)
        attr = f"inner_{verb}"
        if not hasattr(t, attr):
            return None, RTError(
                self.pos_start,
                self.pos_end,
                f"Object of type '{t.__name__}' has no property of name '{verb}'",
                self.context,
            )
        return getattr(t, attr), None

    def set_dot(self, verb: str, value: "Value") -> ValueResult:
        return None, self.illegal_operation(verb, value)

    def copy(self) -> "Value":
        raise Exception('No copy method defined')

    def is_true(self) -> bool:
        return False

    def illegal_operation(self, *others: object) -> RTError:
        if len(others) == 0:
            others = (self,)

        last = others[-1]
        pos_end = getattr(last, "pos_end", None) or self.pos_end

        return RTError(
            self.pos_start,
            pos_end,
            'Illegal operation',
            self.context,
        )
# RUNTIME RESULT
#######################################


class RTResult:
    def __init__(self):
        self.reset()

    def reset(self):
        self.value = None
        self.error = None
        self.func_return_value = None
        self.loop_should_continue = False
        self.loop_should_break = False

    def register(self, res):
        self.error = res.error
        self.func_return_value = res.func_return_value
        self.loop_should_continue = res.loop_should_continue
        self.loop_should_break = res.loop_should_break
        return res.value

    def success(self, value):
        self.reset()
        self.value = value
        return self

    def success_return(self, value):
        self.reset()
        self.func_return_value = value
        return self

    def success_continue(self):
        self.reset()
        self.loop_should_continue = True
        return self

    def success_break(self):
        self.reset()
        self.loop_should_break = True
        return self

    def failure(self, error):
        self.reset()
        self.error = error
        return self

    def should_return(self):
        # Note: this will allow you to continue and break outside the current function
        return (
            self.error or
            self.func_return_value or
            self.loop_should_continue or
            self.loop_should_break
        )

#######################################
# VALUES
#######################################


class Number(Value):
    null: ClassVar["Number"]
    false: ClassVar["Number"]
    true: ClassVar["Number"]
    math_PI: ClassVar["Number"]

    def __init__(self, value):
        super().__init__()
        self.value = value

    def added_to(self, other):
        if isinstance(other, Number):
            return Number(self.value + other.value).set_context(self.context), None
        if isinstance(other, String):
            return String(str(self.value) + other.value).set_context(self.context), None
        return None, Value.illegal_operation(self, other)

    def subbed_by(self, other):
        if isinstance(other, Number):
            return Number(self.value - other.value).set_context(self.context), None
        else:
            return None, Value.illegal_operation(self, other)

    def multed_by(self, other):
        if isinstance(other, Number):
            return Number(self.value * other.value).set_context(self.context), None
        else:
            return None, Value.illegal_operation(self, other)

    def dived_by(self, other):
        if isinstance(other, Number):
            if other.value == 0:
                return None, RTError(
                    other.pos_start, other.pos_end,
                    'Division by zero',
                    self.context
                )

            return Number(self.value / other.value).set_context(self.context), None
        else:
            return None, Value.illegal_operation(self, other)

    def modded_by(self, other):
        if isinstance(other, Number):
            if other.value == 0:
                return None, RTError(
                    other.pos_start, other.pos_end,
                    'Modulo by zero',
                    self.context
                )

            return Number(self.value % other.value).set_context(self.context), None
        else:
            return None, Value.illegal_operation(self, other)

    def powed_by(self, other):
        if isinstance(other, Number):
            return Number(self.value ** other.value).set_context(self.context), None
        else:
            return None, Value.illegal_operation(self, other)

    def get_comparison_eq(self, other):
        if isinstance(other, Number):
            return Number(int(self.value == other.value)).set_context(self.context), None
        else:
            return None, Value.illegal_operation(self, other)

    def get_comparison_ne(self, other):
        if isinstance(other, Number):
            return Number(int(self.value != other.value)).set_context(self.context), None
        else:
            return None, Value.illegal_operation(self, other)

    def get_comparison_lt(self, other):
        if isinstance(other, Number):
            return Number(int(self.value < other.value)).set_context(self.context), None
        else:
            return None, Value.illegal_operation(self, other)

    def get_comparison_gt(self, other):
        if isinstance(other, Number):
            return Number(int(self.value > other.value)).set_context(self.context), None
        else:
            return None, Value.illegal_operation(self, other)

    def get_comparison_lte(self, other):
        if isinstance(other, Number):
            return Number(int(self.value <= other.value)).set_context(self.context), None
        else:
            return None, Value.illegal_operation(self, other)

    def get_comparison_gte(self, other):
        if isinstance(other, Number):
            return Number(int(self.value >= other.value)).set_context(self.context), None
        else:
            return None, Value.illegal_operation(self, other)

    def anded_by(self, other):
        if isinstance(other, Number):
            return Number(int(self.value and other.value)).set_context(self.context), None
        else:
            return None, Value.illegal_operation(self, other)

    def ored_by(self, other):
        if isinstance(other, Number):
            return Number(int(self.value or other.value)).set_context(self.context), None
        else:
            return None, Value.illegal_operation(self, other)

    def notted(self):
        return Number(1 if self.value == 0 else 0).set_context(self.context), None

    def copy(self):
        copy = Number(self.value)
        copy.set_pos(self.pos_start, self.pos_end)
        copy.set_context(self.context)
        return copy

    def is_true(self):
        return self.value != 0

    def __str__(self):
        return str(self.value)

    def __repr__(self):
        return str(self.value)


Number.null = Number(0)
Number.false = Number(0)
Number.true = Number(1)
Number.math_PI = Number(math.pi)


class String(Value):
    def __init__(self, value):
        super().__init__()
        self.value = value

    def added_to(self, other):
        if isinstance(other, String):
            return String(self.value + other.value).set_context(self.context), None
        if isinstance(other, Value):
            return String(self.value + str(other)).set_context(self.context), None
        return None, Value.illegal_operation(self, other)

    def multed_by(self, other):
        if isinstance(other, Number):
            return String(self.value * other.value).set_context(self.context), None
        else:
            return None, Value.illegal_operation(self, other)

    def gen(self):
        for char in self.value:
            yield RTResult().success(String(char))

    def get_index(self, index):
        if not isinstance(index, Number):
            return None, self.illegal_operation(index)
        try:
            return self.value[index.value], None
        except IndexError:
            return None, RTError(
                index.pos_start, index.pos_end,
                f"Cannot retrieve character {index} from string {self!r} because it is out of bounds.",
                self.context
            )

    def get_comparison_eq(self, other):
        if not isinstance(other, String):
            return None, self.illegal_operation(other)
        return Number(int(self.value == other.value)), None

    def get_comparison_ne(self, other):
        if not isinstance(other, String):
            return None, self.illegal_operation(other)
        return Number(int(self.value != other.value)), None

    def is_true(self):
        return len(self.value) > 0

    def copy(self):
        copy = String(self.value)
        copy.set_pos(self.pos_start, self.pos_end)
        copy.set_context(self.context)
        return copy

    def __str__(self):
        return self.value

    def __repr__(self):
        return f'"{self.value}"'


class List(Value):
    def __init__(self, elements):
        super().__init__()
        self.elements = elements
        self.value = elements

    def added_to(self, other):
        new_list = self.copy()
        new_list.elements.append(other)
        return new_list, None

    def subbed_by(self, other):
        if isinstance(other, Number):
            new_list = self.copy()
            try:
                new_list.elements.pop(other.value)
                return new_list, None
            except:
                return None, RTError(
                    other.pos_start, other.pos_end,
                    'Element at this index could not be removed from list because index is out of bounds',
                    self.context
                )
        else:
            return None, Value.illegal_operation(self, other)

    def multed_by(self, other):
        if isinstance(other, List):
            new_list = self.copy()
            new_list.elements.extend(other.elements)
            return new_list, None
        else:
            return None, Value.illegal_operation(self, other)

    def dived_by(self, other):
        if isinstance(other, Number):
            try:
                return self.elements[other.value], None
            except:
                return None, RTError(
                    other.pos_start, other.pos_end,
                    'Element at this index could not be retrieved from list because index is out of bounds',
                    self.context
                )
        else:
            return None, Value.illegal_operation(self, other)

    def gen(self):
        for elt in self.elements:
            yield RTResult().success(elt)

    def get_index(self, index):
        if not isinstance(index, Number):
            return None, self.illegal_operation(index)
        try:
            return self.elements[index.value], None
        except IndexError:
            return None, RTError(
                index.pos_start, index.pos_end,
                f"Cannot retrieve element {index} from list {self!r} because it is out of bounds.",
                self.context
            )

    def set_index(self, index, value):
        if not isinstance(index, Number):
            return None, self.illegal_operation(index)
        try:
            self.elements[index.value] = value
        except IndexError:
            return None, RTError(
                index.pos_start, index.pos_end,
                f"Cannot set element {index} from list {self!r} to {value!r} because it is out of bounds.",
                self.context
            )

        return self, None

    def copy(self):
        copy = List(self.elements)
        copy.set_pos(self.pos_start, self.pos_end)
        copy.set_context(self.context)
        return copy

    def __str__(self):
        return ", ".join([str(x) for x in self.elements])

    def __repr__(self):
        return f'[{", ".join([repr(x) for x in self.elements])}]'


class BaseFunction(Value):
    def __init__(self, name):
        super().__init__()
        self.name = name or "<anonymous>"

    def set_context(self, context=None):
        if hasattr(self, "context") and self.context:
            return self
        return super().set_context(context)

    def generate_new_context(self):
        new_context = Context(self.name, self.context, self.pos_start)
        assert new_context.parent is not None
        assert new_context.parent.symbol_table is not None
        new_context.symbol_table = SymbolTable(new_context.parent.symbol_table)
        return new_context

    def check_args(self, arg_names, args, defaults):
        res = RTResult()

        if len(args) > len(arg_names):
            return res.failure(RTError(
                self.pos_start, self.pos_end,
                f"{len(args) - len(arg_names)} too many args passed into {self}",
                self.context
            ))

        if len(args) < len(arg_names) - len(list(filter(lambda default: default is not None, defaults))):
            return res.failure(RTError(
                self.pos_start, self.pos_end,
                f"{(len(arg_names) - len(list(filter(lambda default: default is not None, defaults)))) - len(args)} too few args passed into {self}",
                self.context
            ))

        return res.success(None)

    def populate_args(self, arg_names, args, defaults, dynamics, exec_ctx):
        res = RTResult()
        assert exec_ctx.symbol_table is not None
        for i in range(len(arg_names)):
            arg_name = arg_names[i]
            dynamic = dynamics[i]
            arg_value = defaults[i] if i >= len(args) else args[i]
            if dynamic is not None:
                dynamic_context = Context(
                    f"{self.name} (dynamic argument '{arg_name}')", exec_ctx, dynamic.pos_start.copy())
                dynamic_context.symbol_table = SymbolTable(exec_ctx.symbol_table)
                dynamic_context.symbol_table.set("$", arg_value)
                arg_value = res.register(
                    Interpreter().visit(dynamic, dynamic_context))
                if res.should_return():
                    return res
            arg_value.set_context(exec_ctx)
            exec_ctx.symbol_table.set(arg_name, arg_value)
        return res.success(None)

    def check_and_populate_args(self, arg_names, args, defaults, dynamics, exec_ctx):
        res = RTResult()
        res.register(self.check_args(arg_names, args, defaults))
        if res.should_return():
            return res
        res.register(self.populate_args(
            arg_names, args, defaults, dynamics, exec_ctx))
        if res.should_return():
            return res
        return res.success(None)


class Function(BaseFunction):
    def __init__(self, name, body_node, arg_names, defaults, dynamics, should_auto_return):
        super().__init__(name)
        self.body_node = body_node
        self.arg_names = arg_names
        self.defaults = defaults
        self.dynamics = dynamics
        self.should_auto_return = should_auto_return

    def execute(self, args):
        res = RTResult()
        interpreter = Interpreter()
        exec_ctx = self.generate_new_context()

        res.register(self.check_and_populate_args(self.arg_names,
                     args, self.defaults, self.dynamics, exec_ctx))
        if res.should_return():
            return res

        value = res.register(interpreter.visit(self.body_node, exec_ctx))
        if res.should_return() and res.func_return_value == None:
            return res

        ret_value = (
            value if self.should_auto_return else None) or res.func_return_value or Number.null
        return res.success(ret_value)

    def copy(self):
        copy = Function(self.name, self.body_node, self.arg_names,
                        self.defaults, self.dynamics, self.should_auto_return)
        copy.set_context(self.context)
        copy.set_pos(self.pos_start, self.pos_end)
        return copy

    def __repr__(self):
        return f"<function {self.name}>"


class PyFunction(BaseFunction):
    def __init__(self, name: str, func: Callable[..., Any]):
        super().__init__(name)
        self.func = func

    def execute(self, args):
        res = RTResult()
        try:
            py_args = [value_to_py(arg) for arg in args]
            result = self.func(*py_args)
        except Exception as exc:
            return res.failure(RTError(
                self.pos_start, self.pos_end,
                f"Python error in {self.name}: {exc}",
                self.context,
            ))

        return res.success(py_to_value(result, self.context, self.pos_start))

    def copy(self):
        copy = PyFunction(self.name, self.func)
        copy.set_context(self.context)
        copy.set_pos(self.pos_start, self.pos_end)
        return copy

    def __repr__(self):
        return f"<py-function {self.name}>"


class BuiltinMethod(Protocol):
    arg_names: list[str]
    defaults: list[Any]
    dynamics: list[Any]

    def __call__(self, exec_ctx: "Context") -> "RTResult":
        ...


class BuiltInFunction(BaseFunction):
    print: ClassVar["BuiltInFunction"]
    print_ret: ClassVar["BuiltInFunction"]
    input: ClassVar["BuiltInFunction"]
    input_int: ClassVar["BuiltInFunction"]
    clear: ClassVar["BuiltInFunction"]
    is_number: ClassVar["BuiltInFunction"]
    is_string: ClassVar["BuiltInFunction"]
    is_list: ClassVar["BuiltInFunction"]
    is_function: ClassVar["BuiltInFunction"]
    append: ClassVar["BuiltInFunction"]
    pop: ClassVar["BuiltInFunction"]
    extend: ClassVar["BuiltInFunction"]
    len: ClassVar["BuiltInFunction"]
    range: ClassVar["BuiltInFunction"]
    map: ClassVar["BuiltInFunction"]
    filter: ClassVar["BuiltInFunction"]
    reduce: ClassVar["BuiltInFunction"]
    join: ClassVar["BuiltInFunction"]
    split: ClassVar["BuiltInFunction"]
    trim: ClassVar["BuiltInFunction"]
    ltrim: ClassVar["BuiltInFunction"]
    rtrim: ClassVar["BuiltInFunction"]
    startswith: ClassVar["BuiltInFunction"]
    endswith: ClassVar["BuiltInFunction"]
    contains: ClassVar["BuiltInFunction"]
    run: ClassVar["BuiltInFunction"]
    open: ClassVar["BuiltInFunction"]
    read: ClassVar["BuiltInFunction"]
    write: ClassVar["BuiltInFunction"]
    close: ClassVar["BuiltInFunction"]
    wait: ClassVar["BuiltInFunction"]

    def __init__(self, name):
        super().__init__(name)

    def execute(self, args):
        res = RTResult()
        exec_ctx = self.generate_new_context()

        method_name = f'execute_{self.name}'
        method = cast(BuiltinMethod, getattr(self, method_name, self.no_execute_method))

        res.register(self.check_and_populate_args(method.arg_names,
                     args, method.defaults, method.dynamics, exec_ctx))
        if res.should_return():
            return res

        return_value = res.register(method(exec_ctx))
        if res.should_return():
            return res
        return res.success(return_value)

    def no_execute_method(self, exec_ctx: "Context"):
        raise Exception(f'No execute_{self.name} method defined')

    def copy(self):
        copy = BuiltInFunction(self.name)
        copy.set_context(self.context)
        copy.set_pos(self.pos_start, self.pos_end)
        return copy

    def __repr__(self):
        return f"<built-in function {self.name}>"

    #####################################

    # Decorator for built-in functions
    @staticmethod
    def args(arg_names, defaults=None, dynamics=None):
        if defaults is None:
            defaults = [None] * len(arg_names)
        if dynamics is None:
            dynamics = [None] * len(arg_names)

        def _args(f):
            f.arg_names = arg_names
            f.defaults = defaults
            f.dynamics = dynamics
            return f
        return _args

    #####################################

    @args(['value'])
    def execute_print(self, exec_ctx):
        print(str(exec_ctx.symbol_table.get('value')))
        return RTResult().success(Number.null)

    @args(['value'])
    def execute_print_ret(self, exec_ctx):
        return RTResult().success(String(str(exec_ctx.symbol_table.get('value'))))

    @args([])
    def execute_input(self, exec_ctx):
        text = input()
        return RTResult().success(String(text))

    @args([])
    def execute_input_int(self, exec_ctx):
        while True:
            text = input()
            try:
                number = int(text)
                break
            except ValueError:
                print(f"'{text}' must be an integer. Try again!")
        return RTResult().success(Number(number))

    @args([])
    def execute_clear(self, exec_ctx):
        os.system('cls' if os.name == 'nt' else 'cls')
        return RTResult().success(Number.null)

    @args(["value"])
    def execute_is_number(self, exec_ctx):
        is_number = isinstance(exec_ctx.symbol_table.get("value"), Number)
        return RTResult().success(Number.true if is_number else Number.false)

    @args(["value"])
    def execute_is_string(self, exec_ctx):
        is_number = isinstance(exec_ctx.symbol_table.get("value"), String)
        return RTResult().success(Number.true if is_number else Number.false)

    @args(["value"])
    def execute_is_list(self, exec_ctx):
        is_number = isinstance(exec_ctx.symbol_table.get("value"), List)
        return RTResult().success(Number.true if is_number else Number.false)

    @args(["value"])
    def execute_is_function(self, exec_ctx):
        is_number = isinstance(
            exec_ctx.symbol_table.get("value"), BaseFunction)
        return RTResult().success(Number.true if is_number else Number.false)

    @args(["list", "value"])
    def execute_append(self, exec_ctx):
        list_ = exec_ctx.symbol_table.get("list")
        value = exec_ctx.symbol_table.get("value")

        if not isinstance(list_, List):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "First argument must be list",
                exec_ctx
            ))

        list_.elements.append(value)
        return RTResult().success(Number.null)

    @args(["list", "index"])
    def execute_pop(self, exec_ctx):
        list_ = exec_ctx.symbol_table.get("list")
        index = exec_ctx.symbol_table.get("index")

        if not isinstance(list_, List):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "First argument must be list",
                exec_ctx
            ))

        if not isinstance(index, Number):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "Second argument must be number",
                exec_ctx
            ))

        try:
            element = list_.elements.pop(index.value)
        except:
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                'Element at this index could not be removed from list because index is out of bounds',
                exec_ctx
            ))
        return RTResult().success(element)

    @args(["listA", "listB"])
    def execute_extend(self, exec_ctx):
        listA = exec_ctx.symbol_table.get("listA")
        listB = exec_ctx.symbol_table.get("listB")

        if not isinstance(listA, List):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "First argument must be list",
                exec_ctx
            ))

        if not isinstance(listB, List):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "Second argument must be list",
                exec_ctx
            ))

        listA.elements.extend(listB.elements)
        return RTResult().success(Number.null)

    @args(["list"])
    def execute_len(self, exec_ctx):
        list_ = exec_ctx.symbol_table.get("list")

        if not isinstance(list_, List):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "Argument must be list",
                exec_ctx
            ))

        return RTResult().success(Number(len(list_.elements)))

    @args(["start", "end", "step"], [None, None, Number(1)])
    def execute_range(self, exec_ctx):
        start = exec_ctx.symbol_table.get("start")
        end = exec_ctx.symbol_table.get("end")
        step = exec_ctx.symbol_table.get("step")

        if not isinstance(start, Number):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "First argument must be number",
                exec_ctx
            ))
        if not isinstance(end, Number):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "Second argument must be number",
                exec_ctx
            ))
        if not isinstance(step, Number):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "Third argument must be number",
                exec_ctx
            ))
        if step.value == 0:
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "Step cannot be 0",
                exec_ctx
            ))

        elements = []
        i = start.value
        if step.value >= 0:
            while i < end.value:
                elements.append(Number(i))
                i += step.value
        else:
            while i > end.value:
                elements.append(Number(i))
                i += step.value

        return RTResult().success(List(elements))

    @args(["list", "func"])
    def execute_map(self, exec_ctx):
        res = RTResult()
        list_ = exec_ctx.symbol_table.get("list")
        func = exec_ctx.symbol_table.get("func")

        if not isinstance(list_, List):
            return res.failure(RTError(
                self.pos_start, self.pos_end,
                "First argument must be list",
                exec_ctx
            ))
        if not isinstance(func, BaseFunction):
            return res.failure(RTError(
                self.pos_start, self.pos_end,
                "Second argument must be function",
                exec_ctx
            ))

        results = []
        for element in list_.elements:
            value = res.register(func.execute([element]))
            if res.should_return():
                return res
            results.append(value)

        return res.success(List(results))

    @args(["list", "func"])
    def execute_filter(self, exec_ctx):
        res = RTResult()
        list_ = exec_ctx.symbol_table.get("list")
        func = exec_ctx.symbol_table.get("func")

        if not isinstance(list_, List):
            return res.failure(RTError(
                self.pos_start, self.pos_end,
                "First argument must be list",
                exec_ctx
            ))
        if not isinstance(func, BaseFunction):
            return res.failure(RTError(
                self.pos_start, self.pos_end,
                "Second argument must be function",
                exec_ctx
            ))

        results = []
        for element in list_.elements:
            value = res.register(func.execute([element]))
            if res.should_return():
                return res
            if value is not None and value.is_true():
                results.append(element)

        return res.success(List(results))

    @args(["list", "func", "initial"])
    def execute_reduce(self, exec_ctx):
        res = RTResult()
        list_ = exec_ctx.symbol_table.get("list")
        func = exec_ctx.symbol_table.get("func")
        initial = exec_ctx.symbol_table.get("initial")

        if not isinstance(list_, List):
            return res.failure(RTError(
                self.pos_start, self.pos_end,
                "First argument must be list",
                exec_ctx
            ))
        if not isinstance(func, BaseFunction):
            return res.failure(RTError(
                self.pos_start, self.pos_end,
                "Second argument must be function",
                exec_ctx
            ))

        result = initial
        for element in list_.elements:
            args: list[Value] = [result, element]
            result = res.register(func.execute(args))
            if res.should_return():
                return res

        return res.success(result)

    @args(["list", "sep"])
    def execute_join(self, exec_ctx):
        list_ = exec_ctx.symbol_table.get("list")
        sep = exec_ctx.symbol_table.get("sep")

        if not isinstance(list_, List):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "First argument must be list",
                exec_ctx
            ))
        if not isinstance(sep, String):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "Second argument must be string",
                exec_ctx
            ))

        result = sep.value.join([str(x) for x in list_.elements])
        return RTResult().success(String(result))

    @args(["text", "sep"])
    def execute_split(self, exec_ctx):
        text = exec_ctx.symbol_table.get("text")
        sep = exec_ctx.symbol_table.get("sep")

        if not isinstance(text, String):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "First argument must be string",
                exec_ctx
            ))
        if not isinstance(sep, String):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "Second argument must be string",
                exec_ctx
            ))
        if sep.value == "":
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "Separator cannot be empty",
                exec_ctx
            ))

        parts = [String(part) for part in text.value.split(sep.value)]
        return RTResult().success(List(parts))

    @args(["text"])
    def execute_trim(self, exec_ctx):
        text = exec_ctx.symbol_table.get("text")
        if not isinstance(text, String):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "Argument must be string",
                exec_ctx
            ))
        return RTResult().success(String(text.value.strip()))

    @args(["text"])
    def execute_ltrim(self, exec_ctx):
        text = exec_ctx.symbol_table.get("text")
        if not isinstance(text, String):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "Argument must be string",
                exec_ctx
            ))
        return RTResult().success(String(text.value.lstrip()))

    @args(["text"])
    def execute_rtrim(self, exec_ctx):
        text = exec_ctx.symbol_table.get("text")
        if not isinstance(text, String):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "Argument must be string",
                exec_ctx
            ))
        return RTResult().success(String(text.value.rstrip()))

    @args(["text", "prefix"])
    def execute_startswith(self, exec_ctx):
        text = exec_ctx.symbol_table.get("text")
        prefix = exec_ctx.symbol_table.get("prefix")
        if not isinstance(text, String):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "First argument must be string",
                exec_ctx
            ))
        if not isinstance(prefix, String):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "Second argument must be string",
                exec_ctx
            ))
        return RTResult().success(Number.true if text.value.startswith(prefix.value) else Number.false)

    @args(["text", "suffix"])
    def execute_endswith(self, exec_ctx):
        text = exec_ctx.symbol_table.get("text")
        suffix = exec_ctx.symbol_table.get("suffix")
        if not isinstance(text, String):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "First argument must be string",
                exec_ctx
            ))
        if not isinstance(suffix, String):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "Second argument must be string",
                exec_ctx
            ))
        return RTResult().success(Number.true if text.value.endswith(suffix.value) else Number.false)

    @args(["text", "part"])
    def execute_contains(self, exec_ctx):
        text = exec_ctx.symbol_table.get("text")
        part = exec_ctx.symbol_table.get("part")
        if not isinstance(text, String):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "First argument must be string",
                exec_ctx
            ))
        if not isinstance(part, String):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "Second argument must be string",
                exec_ctx
            ))
        return RTResult().success(Number.true if part.value in text.value else Number.false)

    @args(["fn"])
    def execute_run(self, exec_ctx):
        fn = exec_ctx.symbol_table.get("fn")

        if not isinstance(fn, String):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "Second argument must be string",
                exec_ctx
            ))

        print("WARNING: run() is deprecated. Use 'IMPORT' instead")
        fn = fn.value

        try:
            with open(fn, "r") as f:
                script = f.read()
        except Exception as e:
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                f"Failed to load script \"{fn}\"\n" + str(e),
                exec_ctx
            ))

        _, error = run(fn, script)

        if error:
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                f"Failed to finish executing script \"{fn}\"\n" +
                error.as_string(),
                exec_ctx
            ))

        return RTResult().success(Number.null)

    @args(["fn", "mode"], [None, String("r")])
    def execute_open(self, exec_ctx):
        sym = exec_ctx.symbol_table
        fake_pos = create_fake_pos("<built-in function open>")
        res = RTResult()

        fn = sym.get("fn")
        if not isinstance(fn, String):
            return res.failure(RTError(
                fake_pos, fake_pos,
                f"1st argument of function 'open' ('fn') must be String",
                exec_ctx
            ))
        fn = fn.value

        mode = sym.get("mode")
        if not isinstance(mode, String):
            return res.failure(RTError(
                fake_pos, fake_pos,
                f"2nd argument of function 'open' ('mode') must be String",
                exec_ctx
            ))
        mode = mode.value

        try:
            f = open(fn, mode)
        except (TypeError, OSError) as err:
            if isinstance(err, TypeError):
                return res.failure(RTError(
                    fake_pos, fake_pos,
                    f"Invalid file open mode: '{mode}'",
                    exec_ctx
                ))
            elif isinstance(err, FileNotFoundError):
                return res.failure(RTError(
                    fake_pos, fake_pos,
                    f"Cannot find file '{fn}'",
                    exec_ctx
                ))
            else:
                return res.failure(RTError(
                    fake_pos, fake_pos,
                    f"{err.args[-1]}",
                    exec_ctx
                ))

        fd = f.fileno()
        files[fd] = f

        return res.success(Number(fd).set_pos(fake_pos, fake_pos).set_context(exec_ctx))

    @args(["fd", "bytes"])
    def execute_read(self, exec_ctx):
        sym = exec_ctx.symbol_table
        fake_pos = create_fake_pos("<built-in function read>")
        res = RTResult()

        fd = sym.get("fd")
        if not isinstance(fd, Number):
            return res.failure(RTError(
                fake_pos, fake_pos,
                f"1st argument of function 'read' ('fd') must be Number",
                exec_ctx
            ))
        fd = fd.value

        bts = sym.get("bytes")
        if not isinstance(bts, Number):
            return res.failure(RTError(
                fake_pos, fake_pos,
                f"2nd argument of function 'read' ('bytes') must be Number",
                exec_ctx
            ))
        bts = bts.value

        try:
            result = os.read(fd, bts).decode("utf-8")
        except OSError:
            return res.failure(RTError(
                fake_pos, fake_pos,
                f"Invalid file descriptor: {fd}",
                exec_ctx
            ))

        return res.success(String(result).set_pos(fake_pos, fake_pos).set_context(exec_ctx))

    @args(["fd", "bytes"])
    def execute_write(self, exec_ctx):
        sym = exec_ctx.symbol_table
        fake_pos = create_fake_pos("<built-in function write>")
        res = RTResult()

        fd = sym.get("fd")
        if not isinstance(fd, Number):
            return res.failure(RTError(
                fake_pos, fake_pos,
                f"1st argument of function 'write' ('fd') must be Number",
                exec_ctx
            ))
        fd = fd.value

        bts = sym.get("bytes")
        if not isinstance(bts, String):
            return res.failure(RTError(
                fake_pos, fake_pos,
                f"2nd argument of function 'write' ('bytes') must be String",
                exec_ctx
            ))
        bts = bts.value

        try:
            num = os.write(fd, bytes(bts, "utf-8"))
        except OSError:
            return res.failure(RTError(
                fake_pos, fake_pos,
                f"Invalid file descriptor: {fd}",
                exec_ctx
            ))

        return res.success(Number(num).set_pos(fake_pos, fake_pos).set_context(exec_ctx))

    @args(["fd"])
    def execute_close(self, exec_ctx):
        sym = exec_ctx.symbol_table
        fake_pos = create_fake_pos("<built-in function close>")
        res = RTResult()

        fd = sym.get("fd")
        if not isinstance(fd, Number):
            return res.failure(RTError(
                fake_pos, fake_pos,
                f"1st argument of function 'close' ('fd') must be Number",
                exec_ctx
            ))
        fd = fd.value
        std_desc = ["stdin", "stdout", "stderr"]

        if fd < 3:
            return res.failure(RTError(
                fake_pos, fake_pos,
                f"Cannot close {std_desc[fd]}",
                exec_ctx
            ))

        try:
            os.close(fd)
        except OSError:
            return res.failure(RTError(
                fake_pos, fake_pos,
                f"Invalid file descriptor '{fd}'",
                exec_ctx
            ))

        del files[fd]

        return res.success(Number.null)

    @args(["secs"])
    def execute_wait(self, exec_ctx):
        sym = exec_ctx.symbol_table
        fake_pos = create_fake_pos("<built-in function wait>")
        res = RTResult()

        secs = sym.get("secs")
        if not isinstance(secs, Number):
            return res.failure(RTError(
                fake_pos, fake_pos,
                f"1st argument of function 'wait' ('secs') must be Number",
                exec_ctx
            ))
        secs = secs.value

        time.sleep(secs)

        return RTResult().success(Number.null)



BuiltInFunction.print = BuiltInFunction("print")
BuiltInFunction.print_ret = BuiltInFunction("print_ret")
BuiltInFunction.input = BuiltInFunction("input")
BuiltInFunction.input_int = BuiltInFunction("input_int")
BuiltInFunction.clear = BuiltInFunction("clear")
BuiltInFunction.is_number = BuiltInFunction("is_number")
BuiltInFunction.is_string = BuiltInFunction("is_string")
BuiltInFunction.is_list = BuiltInFunction("is_list")
BuiltInFunction.is_function = BuiltInFunction("is_function")
BuiltInFunction.append = BuiltInFunction("append")
BuiltInFunction.pop = BuiltInFunction("pop")
BuiltInFunction.extend = BuiltInFunction("extend")
BuiltInFunction.len = BuiltInFunction("len")
BuiltInFunction.range = BuiltInFunction("range")
BuiltInFunction.map = BuiltInFunction("map")
BuiltInFunction.filter = BuiltInFunction("filter")
BuiltInFunction.reduce = BuiltInFunction("reduce")
BuiltInFunction.join = BuiltInFunction("join")
BuiltInFunction.split = BuiltInFunction("split")
BuiltInFunction.trim = BuiltInFunction("trim")
BuiltInFunction.ltrim = BuiltInFunction("ltrim")
BuiltInFunction.rtrim = BuiltInFunction("rtrim")
BuiltInFunction.startswith = BuiltInFunction("startswith")
BuiltInFunction.endswith = BuiltInFunction("endswith")
BuiltInFunction.contains = BuiltInFunction("contains")
BuiltInFunction.run = BuiltInFunction("run")
BuiltInFunction.open = BuiltInFunction("open")
BuiltInFunction.read = BuiltInFunction("read")
BuiltInFunction.write = BuiltInFunction("write")
BuiltInFunction.close = BuiltInFunction("close")
BuiltInFunction.wait = BuiltInFunction("wait")


class Iterator(Value):
    def __init__(self, generator):
        super().__init__()
        self.it = generator()

    def iter(self):
        return self

    def __iter__(self):
        return self

    def __next__(self):
        return next(self.it)

    def __str__(self):
        return '<iterator>'

    def __repr__(self):
        return str(self)

    def __getattr__(self, attr):
        if attr.startswith("get_comparison_"):
            return lambda self, other: Number(self is other), None

    def copy(self):
        return Iterator(self.it)


class Dict(Value):
    def __init__(self, values: dict[str, "Value"]):
        super().__init__()
        self.values = values
        self.value = values

    def added_to(self, other):
        if not isinstance(other, Dict):
            return None, self.illegal_operation(other)

        other_dict: Dict = cast(Dict, other)
        new_dict: Dict = cast(Dict, self.copy())
        for key, value in other_dict.values.items():
            new_dict.values[key] = value

        return new_dict, None

    def gen(self):
        fake_pos = create_fake_pos("<dict key>")
        for key in self.values.keys():
            key_as_value = String(key).set_pos(
                fake_pos, fake_pos).set_context(self.context)
            yield RTResult().success(key_as_value)

    def get_index(self, index):
        if not isinstance(index, String):
            return None, self.illegal_operation(index)

        try:
            return self.values[index.value], None
        except KeyError:
            return None, RTError(
                self.pos_start, self.pos_end,
                f"Could not find key {index!r} in dict {self!r}",
                self.context
            )

    def set_index(self, index, value):
        if not isinstance(index, String):
            return None, self.illegal_operation(index)

        self.values[index.value] = value

        return self, None

    def __str__(self):
        result = ""
        for key, value in self.values.items():
            result += f"{key}: {value}\n"

        return result[:-1]

    def __repr__(self):
        result = "{"
        for key, value in self.values.items():
            result += f"{key!r}: {value!r}, "

        return result[:-2] + "}"

    def copy(self):
        return Dict(self.values).set_pos(self.pos_start, self.pos_end).set_context(self.context)


class StructInstance(Value):
    def __init__(self, struct_name, fields):
        super().__init__()
        self.struct_name = struct_name
        self.fields = fields

    def __repr__(self):
        result = f"{self.struct_name} {{"
        for key, value in self.fields.items():
            result += f"{key}: {value!r}, "

        return result[:-2] + "}"

    def get_dot(self, verb):
        if verb in self.fields:
            return self.fields[verb].copy(), None
        else:
            return None, RTError(
                self.pos_start, self.pos_end,
                f"Could not find property {verb!r} in struct {self.struct_name!r}",
                self.context)

    def set_dot(self, verb, value):
        if verb in self.fields:
            self.fields[verb] = value
            return Number.null, None
        else:
            return None, RTError(
                self.pos_start, self.pos_end,
                f"Could not find property {verb!r} in struct {self.struct_name!r}",
                self.context)

    def copy(self):
        return StructInstance(self.struct_name, self.fields).set_pos(self.pos_start, self.pos_end).set_context(self.context)


class Module(Value):
    def __init__(self, name, symbols):
        super().__init__()
        self.name = name
        self.symbols = symbols

    def get_dot(self, verb):
        if verb in self.symbols:
            value = self.symbols[verb]
            return value.copy().set_context(self.context), None
        return None, RTError(
            self.pos_start, self.pos_end,
            f"Module '{self.name}' has no member named '{verb}'",
            self.context,
        )

    def set_dot(self, verb, value):
        self.symbols[verb] = value
        return Number.null, None

    def copy(self):
        return Module(self.name, self.symbols).set_pos(self.pos_start, self.pos_end).set_context(self.context)

    def __repr__(self):
        return f"<module {self.name}>"

#######################################
# CONTEXT
#######################################


class Context:
    def __init__(self, display_name, parent=None, parent_entry_pos=None):
        self.display_name = display_name
        self.parent = parent
        self.parent_entry_pos = parent_entry_pos
        self.symbol_table: Optional["SymbolTable"] = None

#######################################
# SYMBOL TABLE
#######################################


class SymbolTable:
    def __init__(self, parent=None):
        self.symbols = {}
        self.structs = {}
        self.parent = parent
        self.const = set()

    def get(self, name):
        value = self.symbols.get(name, None)
        if value == None and self.parent:
            return self.parent.get(name)
        return value

    def set(self, name, value):
        self.symbols[name] = value

    def set_const(self, name, value):
        self.symbols[name] = value
        self.const.add(name)

    def remove(self, name):
        del self.symbols[name]


def value_to_py(value):
    if isinstance(value, Number):
        return value.value
    if isinstance(value, String):
        return value.value
    if isinstance(value, List):
        return [value_to_py(v) for v in value.elements]
    if isinstance(value, Dict):
        return {k: value_to_py(v) for k, v in value.values.items()}
    if isinstance(value, BaseFunction):
        def _call(*py_args):
            fake_pos = create_fake_pos("<py arg>")
            wf_args = [py_to_value(arg, value.context, fake_pos) for arg in py_args]
            res = value.execute(wf_args)
            if res.error:
                raise RuntimeError(res.error.as_string())
            return value_to_py(res.value)

        return _call
    if isinstance(value, Module):
        return {k: value_to_py(v) for k, v in value.symbols.items()}
    return value


def py_to_value(obj, context, pos_start):
    fake_pos = pos_start or create_fake_pos("<py>")
    if isinstance(obj, Value):
        return obj
    if obj is None:
        val = Number.null.copy()
    elif isinstance(obj, bool):
        val = Number.true.copy() if obj else Number.false.copy()
    elif isinstance(obj, (int, float)):
        val = Number(obj)
    elif isinstance(obj, str):
        val = String(obj)
    elif isinstance(obj, (list, tuple)):
        val = List([py_to_value(v, context, fake_pos) for v in obj])
    elif isinstance(obj, dict):
        val = Dict({str(k): py_to_value(v, context, fake_pos) for k, v in obj.items()})
    elif callable(obj):
        name = getattr(obj, "__name__", "py_fn")
        val = PyFunction(name, obj)
    else:
        val = String(str(obj))

    if context is not None:
        val.set_context(context)
    val.set_pos(fake_pos, fake_pos)
    return val


def module_name(parts):
    return ".".join(parts)


def find_module_file(parts):
    for base in IMPORT_PATHS:
        candidate = os.path.join(base, *parts)
        py_candidate = candidate + ".py"
        if os.path.isfile(py_candidate):
            return py_candidate
        wf_candidate = candidate + ".wf"
        if os.path.isfile(wf_candidate):
            return wf_candidate
    return None


def load_module(parts, entry_pos, context):
    name = module_name(parts)
    cached = MODULE_CACHE.get(name)
    if cached is not None:
        return cached, None

    filepath = find_module_file(parts)
    if filepath is None:
        return None, RTError(
            entry_pos, entry_pos,
            f"Can't find module '{name}'",
            context,
        )

    if filepath.endswith(".py"):
        module, error = load_python_module(name, filepath, entry_pos, context)
        if error:
            return None, error
    else:
        with open(filepath, "r") as f:
            code = f.read()

        lexer = Lexer(filepath, code)
        tokens, error = lexer.make_tokens()
        if error:
            return None, error

        parser = Parser(tokens)
        ast = parser.parse()
        if ast.error:
            return None, ast.error

        interpreter = Interpreter()
        module_context = Context(f"<module {name}>", None, entry_pos)
        module_context.symbol_table = SymbolTable(global_symbol_table)
        result = interpreter.visit(ast.node, module_context)
        if result.error:
            return None, result.error

        module = Module(name, module_context.symbol_table.symbols)
    module.set_pos(entry_pos, entry_pos)
    if module.context is None:
        module.set_context(module_context)
    MODULE_CACHE[name] = module
    return module, None


def load_python_module(name, filepath, entry_pos, context):
    spec = importlib.util.spec_from_file_location(f"wolfera_{name.replace('.', '_')}", filepath)
    if spec is None or spec.loader is None:
        return None, RTError(
            entry_pos, entry_pos,
            f"Failed to load python module '{name}'",
            context,
        )

    py_module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(py_module)
    except Exception as exc:
        return None, RTError(
            entry_pos, entry_pos,
            f"Python module '{name}' error: {exc}",
            context,
        )

    exports_func = getattr(py_module, "exports", None)
    if not callable(exports_func):
        return None, RTError(
            entry_pos, entry_pos,
            f"Python module '{name}' must define exports()",
            context,
        )

    try:
        exports = exports_func()
    except Exception as exc:
        return None, RTError(
            entry_pos, entry_pos,
            f"Python module '{name}' exports() failed: {exc}",
            context,
        )

    if not isinstance(exports, dict):
        return None, RTError(
            entry_pos, entry_pos,
            f"Python module '{name}' exports() must return dict",
            context,
        )

    module_context = Context(f"<py module {name}>", None, entry_pos)
    module_context.symbol_table = SymbolTable(global_symbol_table)

    symbols = {}
    for key, value in exports.items():
        if not isinstance(key, str):
            return None, RTError(
                entry_pos, entry_pos,
                f"Python module '{name}' export keys must be strings",
                context,
            )
        symbols[key] = py_to_value(value, module_context, entry_pos)

    module = Module(name, symbols)
    module.set_pos(entry_pos, entry_pos).set_context(module_context)
    return module, None


def attach_module(symbol_table, parts, module):
    if len(parts) == 1:
        symbol_table.set(parts[0], module)
        return

    root_name = parts[0]
    root = symbol_table.get(root_name)
    if not isinstance(root, Module):
        root = Module(root_name, {}).set_context(module.context).set_pos(module.pos_start, module.pos_end)
        symbol_table.set(root_name, root)

    current = root
    for part in parts[1:-1]:
        child = current.symbols.get(part)
        if not isinstance(child, Module):
            child = Module(part, {}).set_context(module.context).set_pos(module.pos_start, module.pos_end)
            current.symbols[part] = child
        current = child

    current.symbols[parts[-1]] = module

#######################################
# INTERPRETER
#######################################


class Interpreter:
    def visit(self, node, context):
        method_name = f'visit_{type(node).__name__}'
        method = getattr(self, method_name, self.no_visit_method)
        return method(node, context)

    def no_visit_method(self, node, context):
        raise Exception(f'No visit_{type(node).__name__} method defined')

    ###################################

    def visit_NumberNode(self, node, context):
        return RTResult().success(
            Number(node.tok.value).set_context(
                context).set_pos(node.pos_start, node.pos_end)
        )

    def visit_StringNode(self, node, context):
        return RTResult().success(
            String(node.tok.value).set_context(
                context).set_pos(node.pos_start, node.pos_end)
        )

    def visit_FStringNode(self, node, context):
        res = RTResult()
        raw = node.tok.value
        result_parts = []
        i = 0
        length = len(raw)

        while i < length:
            ch = raw[i]
            if ch == '{':
                if i + 1 < length and raw[i + 1] == '{':
                    result_parts.append('{')
                    i += 2
                    continue

                end_idx = raw.find('}', i + 1)
                if end_idx == -1:
                    return res.failure(RTError(
                        node.pos_start, node.pos_end,
                        "Unclosed '{' in f-string",
                        context,
                    ))

                expr_text = raw[i + 1:end_idx].strip()
                if not expr_text:
                    return res.failure(RTError(
                        node.pos_start, node.pos_end,
                        "Empty expression in f-string",
                        context,
                    ))

                expr_value = self.eval_fstring_expr(expr_text, context, node.pos_start)
                if isinstance(expr_value, RTResult):
                    if expr_value.error:
                        return expr_value
                    expr_value = expr_value.value
                result_parts.append(str(expr_value))
                i = end_idx + 1
                continue

            if ch == '}' and i + 1 < length and raw[i + 1] == '}':
                result_parts.append('}')
                i += 2
                continue

            result_parts.append(ch)
            i += 1

        return res.success(String("".join(result_parts)).set_context(context).set_pos(node.pos_start, node.pos_end))

    def eval_fstring_expr(self, expr_text, context, pos_start):
        lexer = Lexer("<fstring>", expr_text)
        tokens, error = lexer.make_tokens()
        if error:
            return RTResult().failure(error)

        parser = Parser(tokens)
        ast = parser.parse()
        if ast.error:
            return RTResult().failure(ast.error)

        expr_node = ast.node
        if isinstance(expr_node, ListNode):
            if len(expr_node.element_nodes) != 1:
                return RTResult().failure(RTError(
                    pos_start, pos_start,
                    "f-string expression must be a single expression",
                    context,
                ))
            expr_node = expr_node.element_nodes[0]

        return self.visit(expr_node, context)

    def visit_ListNode(self, node, context):
        res = RTResult()
        elements = []

        for element_node in node.element_nodes:
            elements.append(res.register(self.visit(element_node, context)))
            if res.should_return():
                return res

        return res.success(
            List(elements).set_context(context).set_pos(
                node.pos_start, node.pos_end)
        )

    def visit_VarAccessNode(self, node, context):
        res = RTResult()
        var_name = node.var_name_tok.value
        value = context.symbol_table.get(var_name)

        if not value:
            return res.failure(RTError(
                node.pos_start, node.pos_end,
                f"'{var_name}' is not defined",
                context
            ))

        value = value.copy().set_pos(node.pos_start, node.pos_end).set_context(context)
        return res.success(value)

    def visit_VarAssignNode(self, node, context):
        res = RTResult()
        var_name = node.var_name_tok.value
        value = res.register(self.visit(node.value_node, context))
        if res.should_return():
            return res

        if node.is_const:
            method = context.symbol_table.set_const
        else:
            method = context.symbol_table.set

        if var_name not in context.symbol_table.const:
            method(var_name, value)
            return res.success(value)
        else:
            return res.failure(RTError(
                node.pos_start, node.pos_end,
                f"Assignment to constant variable '{var_name}'",
                context
            ))

    def visit_BinOpNode(self, node, context):
        res = RTResult()
        left = res.register(self.visit(node.left_node, context))
        if res.should_return():
            return res
        right = res.register(self.visit(node.right_node, context))
        if res.should_return():
            return res

        result = None
        error = None

        if node.op_tok.type == TokenType.PLUS:
            result, error = left.added_to(right)
        elif node.op_tok.type == TokenType.MINUS:
            result, error = left.subbed_by(right)
        elif node.op_tok.type == TokenType.MUL:
            result, error = left.multed_by(right)
        elif node.op_tok.type == TokenType.DIV:
            result, error = left.dived_by(right)
        elif node.op_tok.type == TokenType.MOD:
            result, error = left.modded_by(right)
        elif node.op_tok.type == TokenType.POW:
            result, error = left.powed_by(right)
        elif node.op_tok.type == TokenType.EE:
            result, error = left.get_comparison_eq(right)
        elif node.op_tok.type == TokenType.NE:
            result, error = left.get_comparison_ne(right)
        elif node.op_tok.type == TokenType.LT:
            result, error = left.get_comparison_lt(right)
        elif node.op_tok.type == TokenType.GT:
            result, error = left.get_comparison_gt(right)
        elif node.op_tok.type == TokenType.LTE:
            result, error = left.get_comparison_lte(right)
        elif node.op_tok.type == TokenType.GTE:
            result, error = left.get_comparison_gte(right)
        elif node.op_tok.matches(TokenType.KEYWORD, 'and'):
            result, error = left.anded_by(right)
        elif node.op_tok.matches(TokenType.KEYWORD, 'or'):
            result, error = left.ored_by(right)

        if error:
            return res.failure(error)
        else:
            assert result is not None
            return res.success(result.set_pos(node.pos_start, node.pos_end))

    def visit_UnaryOpNode(self, node, context):
        res = RTResult()
        number = res.register(self.visit(node.node, context))
        if res.should_return():
            return res

        error = None

        if node.op_tok.type == TokenType.MINUS:
            number, error = number.multed_by(Number(-1))
        elif node.op_tok.matches(TokenType.KEYWORD, 'not'):
            number, error = number.notted()

        if error:
            return res.failure(error)
        else:
            return res.success(number.set_pos(node.pos_start, node.pos_end))

    def visit_IfNode(self, node, context):
        res = RTResult()

        for condition, expr, should_return_null in node.cases:
            condition_value = res.register(self.visit(condition, context))
            if res.should_return():
                return res

            if condition_value.is_true():
                expr_value = res.register(self.visit(expr, context))
                if res.should_return():
                    return res
                return res.success(Number.null if should_return_null else expr_value)

        if node.else_case:
            expr, should_return_null = node.else_case
            expr_value = res.register(self.visit(expr, context))
            if res.should_return():
                return res
            return res.success(Number.null if should_return_null else expr_value)

        return res.success(Number.null)

    def visit_ForNode(self, node, context):
        res = RTResult()
        elements = []

        start_value = res.register(self.visit(node.start_value_node, context))
        if res.should_return():
            return res

        end_value = res.register(self.visit(node.end_value_node, context))
        if res.should_return():
            return res

        if node.step_value_node:
            step_value = res.register(
                self.visit(node.step_value_node, context))
            if res.should_return():
                return res
        else:
            step_value = Number(1)

        i = start_value.value

        if step_value.value >= 0:
            def condition(): return i < end_value.value
        else:
            def condition(): return i > end_value.value

        while condition():
            context.symbol_table.set(node.var_name_tok.value, Number(i))
            i += step_value.value

            value = res.register(self.visit(node.body_node, context))
            if res.should_return() and res.loop_should_continue == False and res.loop_should_break == False:
                return res

            if res.loop_should_continue:
                continue

            if res.loop_should_break:
                break

            elements.append(value)

        return res.success(
            Number.null if node.should_return_null else
            List(elements).set_context(context).set_pos(
                node.pos_start, node.pos_end)
        )

    def visit_WhileNode(self, node, context):
        res = RTResult()
        elements = []

        while True:
            condition = res.register(self.visit(node.condition_node, context))
            if res.should_return():
                return res

            if not condition.is_true():
                break

            value = res.register(self.visit(node.body_node, context))
            if res.should_return() and res.loop_should_continue == False and res.loop_should_break == False:
                return res

            if res.loop_should_continue:
                continue

            if res.loop_should_break:
                break

            elements.append(value)

        return res.success(
            Number.null if node.should_return_null else
            List(elements).set_context(context).set_pos(
                node.pos_start, node.pos_end)
        )

    def visit_FuncDefNode(self, node, context):
        res = RTResult()

        func_name = node.var_name_tok.value if node.var_name_tok else None
        body_node = node.body_node
        arg_names = [arg_name.value for arg_name in node.arg_name_toks]
        defaults = []
        for default in node.defaults:
            if default is None:
                defaults.append(None)
                continue
            default_value = res.register(self.visit(default, context))
            if res.should_return():
                return res
            defaults.append(default_value)

        func_value = Function(func_name, body_node, arg_names, defaults, node.dynamics,
                              node.should_auto_return).set_context(context).set_pos(node.pos_start, node.pos_end)

        if node.var_name_tok:
            context.symbol_table.set(func_name, func_value)

        return res.success(func_value)

    def visit_CallNode(self, node, context):
        res = RTResult()
        args = []

        value_to_call = res.register(self.visit(node.node_to_call, context))
        if res.should_return():
            return res
        value_to_call = value_to_call.copy().set_pos(node.pos_start, node.pos_end)

        for arg_node in node.arg_nodes:
            args.append(res.register(self.visit(arg_node, context)))
            if res.should_return():
                return res

        return_value = res.register(value_to_call.execute(args))
        if res.should_return():
            return res
        return_value = return_value.copy().set_pos(
            node.pos_start, node.pos_end).set_context(context)
        return res.success(return_value)

    def visit_ReturnNode(self, node, context):
        res = RTResult()

        if node.node_to_return:
            value = res.register(self.visit(node.node_to_return, context))
            if res.should_return():
                return res
        else:
            value = Number.null

        return res.success_return(value)

    def visit_ContinueNode(self, node, context):
        return RTResult().success_continue()

    def visit_BreakNode(self, node, context):
        return RTResult().success_break()

    def visit_ImportNode(self, node, context):
        res = RTResult()
        if isinstance(node.module_path, StringNode):
            filename = res.register(self.visit(node.module_path, context))
            code = None
            filepath = filename.value

            for path in IMPORT_PATHS:
                try:
                    filepath = os.path.join(path, filename.value)
                    with open(filepath, "r") as f:
                        code = f.read()
                        beginning = "/" if filepath.startswith("/") else ""
                        split = filepath.split("/")
                        split = beginning + "/".join(split[:-1]), split[-1]
                        os.chdir(split[0])
                        filename = split[1]
                        break
                except FileNotFoundError:
                    continue

            if code is None:
                return res.failure(RTError(
                    node.module_path.pos_start.copy(), node.module_path.pos_end.copy(),
                    f"Can't find file '{filepath}' in '{IMPORT_PATH_NAME}'. Please add the directory your file is into that file",
                    context
                ))

            _, error = run(filename, code, context, node.pos_start.copy())
            if error:
                return res.failure(error)

            return res.success(Number.null)

        module, error = load_module(node.module_path, node.pos_start.copy(), context)
        if error:
            return res.failure(error)

        assert context.symbol_table is not None
        attach_module(context.symbol_table, node.module_path, module)
        return res.success(Number.null)

    def visit_FromImportNode(self, node, context):
        res = RTResult()
        module, error = load_module(node.module_path, node.pos_start.copy(), context)
        if error:
            return res.failure(error)

        assert context.symbol_table is not None
        for name in node.names:
            if name.value not in module.symbols:
                return res.failure(RTError(
                    node.pos_start.copy(), node.pos_end.copy(),
                    f"Module '{module.name}' has no member named '{name.value}'",
                    context
                ))
            context.symbol_table.set(name.value, module.symbols[name.value])

        return res.success(Number.null)

    def visit_DoNode(self, node, context):
        res = RTResult()
        new_context = Context("<DO statement>", context, node.pos_start.copy())
        assert context.symbol_table is not None
        new_context.symbol_table = SymbolTable(context.symbol_table)
        res.register(self.visit(node.statements, new_context))

        return_value = res.func_return_value
        if res.should_return() and return_value is None:
            return res

        return_value = return_value or Number.null

        return res.success(return_value)

    def visit_TryNode(self, node, context):
        res = RTResult()
        res.register(self.visit(node.try_block, context))
        handled_error = res.error
        if res.should_return() and res.error is None:
            return res

        elif handled_error is not None:
            var_name = node.exc_iden.value
            assert context.symbol_table is not None
            context.symbol_table.set(var_name, res.error)
            res.error = None

            res.register(self.visit(node.catch_block, context))
            if res.error:
                return res.failure(TryError(
                    res.error.pos_start, res.error.pos_end, res.error.details, res.error.context, handled_error
                ))
            return res.success(Number.null)
        else:
            return res.success(Number.null)

    def visit_ForInNode(self, node, context):
        res = RTResult()
        var_name = node.var_name_tok.value
        body = node.body_node
        should_return_null = node.should_return_null

        iterable = res.register(self.visit(node.iterable_node, context))
        it = iterable.iter()

        elements = []

        for it_res in it:
            elt = res.register(it_res)
            if res.should_return():
                return res

            context.symbol_table.set(var_name, elt)

            elements.append(res.register(self.visit(body, context)))
            if res.should_return():
                return res

        if should_return_null:
            return res.success(Number.null)
        return res.success(elements)

    def visit_IndexGetNode(self, node, context):
        res = RTResult()
        indexee = res.register(self.visit(node.indexee, context))
        if res.should_return():
            return res

        index = res.register(self.visit(node.index, context))
        if res.should_return():
            return res

        result, error = indexee.get_index(index)
        if error:
            return res.failure(error)
        return res.success(result)

    def visit_IndexSetNode(self, node, context):
        res = RTResult()
        indexee = res.register(self.visit(node.indexee, context))
        if res.should_return():
            return res

        index = res.register(self.visit(node.index, context))
        if res.should_return():
            return res

        value = res.register(self.visit(node.value, context))
        if res.should_return():
            return res

        result, error = indexee.set_index(index, value)
        if error:
            return res.failure(error)

        return res.success(result)

    def visit_DictNode(self, node, context):
        res = RTResult()
        values = {}

        for key_node, value_node in node.pairs:
            key = res.register(self.visit(key_node, context))
            if res.should_return():
                return res

            if not isinstance(key, String):
                return res.failure(RTError(
                    key_node.pos_start, key_node.pos_end,
                    f"Non-string key for dict: '{key!r}'",
                    context
                ))

            value = res.register(self.visit(value_node, context))
            if res.should_return():
                return res

            values[key.value] = value

        return res.success(Dict(values))

    def visit_SwitchNode(self, node, context):
        res = RTResult()
        condition = res.register(self.visit(node.condition, context))
        if res.should_return():
            return res

        for case, body in node.cases:
            case = res.register(self.visit(case, context))
            if res.should_return():
                return res

            # print(f"[DEBUG] {object.__repr__(case)}")

            eq, error = condition.get_comparison_eq(case)
            if error:
                return res.failure(error)

            if eq.value:
                res.register(self.visit(body, context))
                if res.should_return():
                    return res
                break
        else:  # no break
            else_case = node.else_case
            if else_case:
                res.register(self.visit(else_case, context))
                if res.should_return():
                    return res

        return res.success(Number.null)

    def visit_DotGetNode(self, node, context):
        res = RTResult()
        noun = res.register(self.visit(node.noun, context))
        if res.should_return():
            return res

        verb = node.verb.value

        result, error = noun.get_dot(verb)
        if error:
            return res.failure(error)
        return res.success(result)

    def visit_DotSetNode(self, node, context):
        res = RTResult()
        noun = res.register(self.visit(node.noun, context))
        if res.should_return():
            return res

        verb = node.verb.value

        value = res.register(self.visit(node.value, context))
        if res.should_return():
            return res

        result, error = noun.set_dot(verb, value)
        if error:
            return res.failure(error)

        return res.success(result)

    def visit_StructNode(self, node, ctx):
        # TODO: report struct redefinition
        ctx.symbol_table.structs[node.name] = node.fields
        return RTResult().success(Number.null)

    def visit_StructCreationNode(self, node, ctx):
        res = RTResult()
        struct = ctx.symbol_table.structs[node.name]

        return res.success(StructInstance(node.name, {field: Number.null for field in struct})
                           .set_pos(node.pos_start, node.pos_end)
                           .set_context(ctx))

#######################################
# CREATE FAKE POS
#######################################


def create_fake_pos(desc: str) -> Position:
    return Position(0, 0, 0, desc, "<native code>")  # hmm yes very native

#######################################
# RUN
#######################################


def make_argv(args: Optional[list[str]] = None):
    argv = []
    fake_pos = create_fake_pos("<argv>")
    if args is None:
        args = sys.argv[1:]
    for arg in args:
        argv.append(String(arg).set_pos(fake_pos, fake_pos))
    return List(argv).set_pos(fake_pos, fake_pos)


global_symbol_table = SymbolTable()
global_symbol_table.set("null", Number.null)
global_symbol_table.set("false", Number.false)
global_symbol_table.set("true", Number.true)
global_symbol_table.set("argv", make_argv())
global_symbol_table.set("math_pi", Number.math_PI)
global_symbol_table.set("print", BuiltInFunction.print)
global_symbol_table.set("print_ret", BuiltInFunction.print_ret)
global_symbol_table.set("input", BuiltInFunction.input)
global_symbol_table.set("input_int", BuiltInFunction.input_int)
global_symbol_table.set("clear", BuiltInFunction.clear)
global_symbol_table.set("cls", BuiltInFunction.clear)
global_symbol_table.set("is_num", BuiltInFunction.is_number)
global_symbol_table.set("is_str", BuiltInFunction.is_string)
global_symbol_table.set("is_list", BuiltInFunction.is_list)
global_symbol_table.set("is_fun", BuiltInFunction.is_function)
global_symbol_table.set("append", BuiltInFunction.append)
global_symbol_table.set("pop", BuiltInFunction.pop)
global_symbol_table.set("extend", BuiltInFunction.extend)
global_symbol_table.set("len", BuiltInFunction.len)
global_symbol_table.set("range", BuiltInFunction.range)
global_symbol_table.set("map", BuiltInFunction.map)
global_symbol_table.set("filter", BuiltInFunction.filter)
global_symbol_table.set("reduce", BuiltInFunction.reduce)
global_symbol_table.set("join", BuiltInFunction.join)
global_symbol_table.set("split", BuiltInFunction.split)
global_symbol_table.set("trim", BuiltInFunction.trim)
global_symbol_table.set("ltrim", BuiltInFunction.ltrim)
global_symbol_table.set("rtrim", BuiltInFunction.rtrim)
global_symbol_table.set("startswith", BuiltInFunction.startswith)
global_symbol_table.set("endswith", BuiltInFunction.endswith)
global_symbol_table.set("contains", BuiltInFunction.contains)
global_symbol_table.set("run", BuiltInFunction.run)
global_symbol_table.set("open", BuiltInFunction.open)
global_symbol_table.set("read", BuiltInFunction.read)
global_symbol_table.set("write", BuiltInFunction.write)
global_symbol_table.set("close", BuiltInFunction.close)
global_symbol_table.set("wait", BuiltInFunction.wait)


def run(fn, text, context=None, entry_pos=None, argv: Optional[list[str]] = None):
    if argv is not None:
        global_symbol_table.set("argv", make_argv(argv))

    # Generate tokens
    lexer = Lexer(fn, text)
    tokens, error = lexer.make_tokens()
    if error:
        return None, error

    # Generate AST
    parser = Parser(tokens)
    ast = parser.parse()
    if ast.error:
        return None, ast.error

    # Run program
    interpreter = Interpreter()
    context_was_none = context is None
    context = Context('<program>', context, entry_pos)
    if context_was_none:
        context.symbol_table = global_symbol_table
    else:
        assert context.parent is not None
        assert context.parent.symbol_table is not None
        context.symbol_table = context.parent.symbol_table
    result = interpreter.visit(ast.node, context)
    ret = result.func_return_value
    if context_was_none and ret:
        if not isinstance(ret, Number):
            return None, RTError(
                ret.pos_start, ret.pos_end,
                "Exit code must be Number",
                context,
            )
        exit(ret.value)

    return result.value, result.error
