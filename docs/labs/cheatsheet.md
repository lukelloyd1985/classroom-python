# Python Cheatsheet

*Works in Tablet mode (Skulpt) unless marked (Pi).*

## Output and input
```python
print("Hi", name)               # several values, space between
print("a" + "b")                # join text
name = input("Name? ")          # always returns text
n = int(input("Number? "))      # convert to whole number
x = float(input("Number? "))    # convert to decimal
```

## Types and conversion
| Code | Result |
|---|---|
| `int("5")` | `5` |
| `float("2.5")` | `2.5` |
| `str(5)` | `"5"` |
| `type(x)` | the type of `x` |
| `bool(0)`, `bool("")` | `False` (empty and zero are false) |

## Maths
| Op | Meaning | Op | Meaning |
|---|---|---|---|
| `+ - *` | basic | `//` | whole divide |
| `/` | divide | `%` | remainder |
| `**` | power | `+=  -=  *=` | update variable |

`round(x, 2)`  `abs(x)`  `min(a, b)`  `max(a, b)`  `sum(list)`

## Strings
```python
s = "Hello World"
len(s)              # 11
s.upper()           # "HELLO WORLD"
s.lower()
s.strip()           # remove spaces at the ends
s.replace("o", "0")
s.split(" ")        # ["Hello", "World"]
s[0]  s[-1]  s[0:5] # first, last, slice
"lo" in s           # True
"Name: %s, Age: %d" % ("Sam", 12)    # formatting that works everywhere
```
f-strings, e.g. `f"Hi {name}"` : **(Pi)** only.

## Conditions
```python
if a == b:   ...        # equal        a != b   not equal
elif a < b:  ...        # < > <= >=
else:        ...
a and b     a or b     not a
```

## Loops
```python
for i in range(5): ...          # 0..4
for i in range(1, 11): ...      # 1..10
for i in range(10, 0, -1): ...  # countdown
for item in my_list: ...
while condition: ...
break       # leave loop
continue    # skip to next round
```

## Lists
```python
L = [3, 1, 2]
L.append(4)    L.insert(0, 9)    L.remove(1)    L.pop()
L.sort()       L.reverse()       len(L)
L[0]  L[-1]  L[1:3]
x in L         L.index(2)        L.count(3)
```

## Dictionaries
```python
d = {"a": 1, "b": 2}
d["c"] = 3         d["a"]         d.get("z", 0)
del d["a"]         "b" in d
d.keys()   d.values()   d.items()
for k in d: print(k, d[k])
```

## Functions
```python
def add(a, b=0):
    return a + b
```

## Useful modules
```python
import random
random.randint(1, 6)        # whole number 1..6
random.choice(my_list)

import math
math.sqrt(16)   math.pi   math.floor(2.7)   math.ceil(2.1)
```
`import time`, `import datetime`, `import json` : check they work in Tablet mode; full support **(Pi)**.

## Common errors
| Message | Usual cause |
|---|---|
| `SyntaxError` | missing `:`, bracket or quote |
| `IndentationError` | wrong spaces after `:` (use 4) |
| `NameError` | typo in a name, or used before it is created |
| `TypeError` | e.g. `"5" + 5`: convert with `int()` / `str()` |
| `ValueError` | e.g. `int("abc")` |
| `IndexError` | list position doesn't exist |
| `KeyError` | dictionary key doesn't exist (use `.get`) |
| `ZeroDivisionError` | dividing by 0 |

## Editor tips
- **Run** to start, **Stop** to halt an endless loop, **New** to clear (asks first).
- Code autosaves on your tablet.
- 4 spaces per indent level, always.

## Running Python on your own computer
```sh
python3 hello.py        # run a file
python3                 # interactive prompt (exit with exit() or Ctrl-D)
python3 -m venv .venv   # create a virtual environment
pip install <package>   # install a package
```
