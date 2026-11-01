# 03 Input and Maths

## Asking the user
`input()` always gives back **text**.

```python
name = input("What is your name? ")
print("Hello, " + name)
```

Convert to a number with `int()` or `float()`:

```python
age = int(input("How old are you? "))
print("Next year you will be", age + 1)
```

## Operators
| Operator | Meaning | Example | Result |
|---|---|---|---|
| `+` `-` `*` | add, subtract, multiply | `3 * 4` | `12` |
| `/` | divide (decimal) | `7 / 2` | `3.5` |
| `//` | whole-number divide | `7 // 2` | `3` |
| `%` | remainder | `7 % 2` | `1` |
| `**` | power | `2 ** 3` | `8` |

Brackets work as in maths: `(2 + 3) * 4`.

```python
print(round(3.14159, 2))   # 3.14
print(abs(-5))             # 5
print(max(3, 9, 4))        # 9
```

## Try it
1. Ask for two numbers and print their sum.
2. Ask for a number and say whether it is even (hint: `% 2`).
3. Convert minutes to hours and minutes (use `//` and `%`).
