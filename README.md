# Wolfera

Wolfera is a small, expression‑oriented programming language and interpreter implemented in Python. The syntax is lightweight, focused on readability and fast iteration.

This project is **based on** the language and interpreter from [myopl-plus-plus](https://github.com/angelcaru/myopl-plus-plus), with a streamlined structure, updated syntax choices, and a fully modular codebase.

## Quick Start

1. Run code from a file:
```bash
python3 /Users/chasonick/Documents/Wolfera/main.py /Users/chasonick/Documents/Wolfera/examples/example.wf
```
2. Run a one‑liner:
```bash
python3 /Users/chasonick/Documents/Wolfera/main.py "2 + 3 * 4"
```
3. Print tokens:
```bash
python3 /Users/chasonick/Documents/Wolfera/main.py "2 + 3" --tokens
```
4. Print AST:
```bash
python3 /Users/chasonick/Documents/Wolfera/main.py "2 + 3 * 4" --ast
```

## Language Basics

### Comments

- Single line: `# comment`
- Multi‑line:
```wf
#*
this is a block comment
*#
```

### Variables and Constants

```wf
x = 10
name = "wolfera"
const pi = 3.1415
```

### Types

- Number (int/float)
- String
- List
- Dict (string keys only)
- Function
- Struct
- Module
- Null/Bool: `null`, `true`, `false`

### Operators

- Arithmetic: `+ - * / % ^`
- Comparison: `== != < > <= >=`
- Logical: `and or not`
- Assignment: `=`

### Strings

```wf
print("hello")
print("a" + "b")
print(123 + " - time")  # number + string
```

### F‑Strings

Two supported styles:
```wf
name = "Ada"
print(f"hello {name}")
print(f"sum={1+2}")
```
```wf
print(f"TEST {} TEST {}", 1, 2)
```

### Lists

```wf
nums = [1, 2, 3]
print(nums[0])
nums[1] = 99
```

### Dictionaries

```wf
user = {"name": "Ann", "age": 21}
print(user["name"])
user["age"] = 22
```

Note: dict keys must be strings.

### Structs

```wf
struct Person { name, age }

p = Person{}
p.name = "Ann"
p.age = 21
print(p.name)
```

### Functions

Expression body:
```wf
fun add(a, b) -> a + b
```
Block body:
```wf
fun greet(name) {
	print("hi " + name)
}
```
Default arguments:
```wf
fun add(a, b = 5) -> a + b
```

### Control Flow

```wf
if x > 10 {
	print("big")
} elif x == 10 {
	print("ten")
} else {
	print("small")
}
```

### Loops

For‑range:
```wf
for i = 0 to 5 {
	print(i)
}
```
For‑range with step:
```wf
for i = 0 to 10 step 2 {
	print(i)
}
```
For‑in:
```wf
for item in ["a", "b"] {
	print(item)
}
```
While:
```wf
while x < 5 {
	x = x + 1
}
```

### Switch

```wf
switch x {
	case 1 { print("one") }
	case 2 { print("two") }
	else { print("other") }
}
```

### Try / Catch

```wf
try {
	print(1 / 0)
} catch as err {
	print(err)
}
```

### Scopes / Blocks

`do { ... }` creates a local scope:
```wf
do {
	x = 10
	print(x)
}
```

### Imports and Modules

Wolfera supports two styles:

1) Import a file (executes into current scope):
```wf
import "utils.wf"
```

2) Import modules with dotted paths:
```wf
import time
import std.time
from time import {now, time_exec}
print(time.now())
print(std.time.now())
```

Module search paths are stored in `/Users/chasonick/Documents/Wolfera/.path`.

### Python Modules (Std in Python)

Python modules are allowed if they define `exports()` that returns a dict of names to values:
```python
# std/example.py

def add(a, b):
    return a + b

def exports():
    return {"add": add}
```
Then in Wolfera:
```wf
import example
print(example.add(2, 3))
```

## Built‑in Functions

- `print(value)`
- `print_ret(value)`
- `input()`
- `input_int()`
- `clear()` or `cls()`
- `is_num(value)`
- `is_str(value)`
- `is_list(value)`
- `is_fun(value)`
- `append(list, value)`
- `pop(list, index)`
- `extend(listA, listB)`
- `len(list)`
- `range(start, end, step=1)`
- `map(list, func)`
- `filter(list, func)`
- `reduce(list, func, initial)`
- `join(list, sep)`
- `split(text, sep)`
- `trim(text)`
- `ltrim(text)`
- `rtrim(text)`
- `startswith(text, prefix)`
- `endswith(text, suffix)`
- `contains(text, part)`
- `open(path, mode)`
- `read(fd, bytes)`
- `write(fd, text)`
- `close(fd)`
- `wait(seconds)`

## Standard Libraries

- `std/time.py` (Python):
```wf
import time
print(time.now())
print(time.time_exec(fun() -> 123))
```
- `std/time_wf.wf` (Wolfera wrapper):
```wf
import time_wf
print(time_wf.now())
```

## Errors

Errors include:

- line and column
- a code snippet with caret range
- a helpful hint

Example:
```text
Runtime Error: Illegal operation (line 59, column 18)

59 | print(execu_time - " TEST")
                      ^^^^^^^^^

Hint: Check operand types and whether the operation is supported for them.
```

## CLI Options

- `--tokens` prints tokens
- `--ast` prints the AST

## Notes

- Dict keys must be strings.
- `import` prefers `.py` modules over `.wf` when names match.
- Python modules run with full system access; use with care.
