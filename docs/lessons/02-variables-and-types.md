# 02 Variables and Types

A **variable** is a name that holds a value.

```python
name = "Sam"
age = 12
height = 1.52
likes_pizza = True

print(name, age, height, likes_pizza)
```

## The four basic types
| Type | Example | Notes |
|---|---|---|
| `str` | `"hello"` | text |
| `int` | `42` | whole number |
| `float` | `3.14` | decimal number |
| `bool` | `True` / `False` | capital first letter |

Check with `type()`:
```python
print(type(42))
print(type("42"))
```

## Joining text
```python
first = "Ada"
last = "Lovelace"
print(first + " " + last)
print("Age: " + str(12))   # numbers must become text with str()
print("Age:", 12)          # or use a comma: no str() needed
```

## Changing variables
```python
score = 0
score = score + 10
score += 5          # shorthand for score = score + 5
print(score)
```

## Naming rules
Letters, digits, `_`. Can't start with a digit. No spaces. Use `lower_case_with_underscores`.

## Try it
1. Store your favourite number and print it with a message.
2. What does `print("5" + "5")` show? And `print(5 + 5)`? Why?
3. Make `lives = 3`, subtract one, print it.
