# 07 Functions

A function is a named, reusable block of code. Define it with `def`.

```python
def greet(name):
    print("Hello, " + name + "!")

greet("Sam")
greet("Priya")
```

## Returning a value
```python
def square(n):
    return n * n

result = square(6)
print(result)            # 36
```

## Default values
```python
def power(base, exp=2):
    return base ** exp

print(power(5))          # 25
print(power(2, 10))      # 1024
```

`print` shows things on screen; `return` hands a value back to the caller. They are not the same.

## Variables inside functions
Variables created inside a function only exist inside it (they are *local*).

## Try it
1. Write `double(n)` that returns `n * 2`.
2. Write `is_even(n)` that returns `True` or `False`.
3. Write `average(a, b, c)` and print the result.
