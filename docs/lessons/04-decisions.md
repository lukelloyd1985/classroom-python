# 04 Decisions

`if` runs code only when a condition is true. **Indentation (4 spaces) matters.**

```python
age = int(input("Age? "))
if age >= 18:
    print("Adult")
elif age >= 13:
    print("Teenager")
else:
    print("Child")
```

## Comparisons
`==` equal, `!=` not equal, `<` `>` `<=` `>=`

> `=` stores a value. `==` asks a question. Mixing them up is the #1 beginner bug.

## Combining conditions
```python
if age >= 13 and age <= 19:
    print("Teen")
if day == "Sat" or day == "Sun":
    print("Weekend")
if not raining:
    print("Go outside")
```

## Try it
1. Ask for a password; print "Welcome" if it matches, else "Wrong".
2. Grade a score: 70+ "A", 50+ "B", otherwise "Try again".
3. Ask for a number and print whether it is positive, negative or zero.
