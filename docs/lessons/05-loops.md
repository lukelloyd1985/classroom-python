# 05 Loops

## `for` : repeat a known number of times
```python
for i in range(5):
    print("Round", i)        # 0 1 2 3 4
```
`range(start, stop, step)`: stop is **not** included.
```python
for n in range(1, 11):
    print(n)
for n in range(10, 0, -2):
    print(n)                 # 10 8 6 4 2
```

## `while` : repeat until a condition changes
```python
count = 3
while count > 0:
    print(count)
    count -= 1
print("Liftoff!")
```

## `break` and `continue`
```python
while True:
    word = input("Type quit to stop: ")
    if word == "quit":
        break                # leave the loop
    print("You typed", word)
```

> Endless loop? Press **Stop**. The editor also stops it automatically after a few seconds.

## Try it
1. Print the numbers 1 to 20.
2. Print the 7 times table.
3. Keep asking for a number until the user enters one above 10.
4. Add up the numbers 1 to 100 using a loop.
