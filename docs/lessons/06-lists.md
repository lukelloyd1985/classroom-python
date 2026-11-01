# 06 Lists

A list holds many values in order.

```python
fruits = ["apple", "banana", "cherry"]
print(fruits[0])        # apple (counting starts at 0)
print(fruits[-1])       # cherry (last item)
print(len(fruits))      # 3
```

## Changing a list
```python
fruits.append("date")       # add to the end
fruits.remove("banana")     # remove by value
fruits[0] = "apricot"       # replace
fruits.sort()               # alphabetical order
```

## Looping over a list
```python
for fruit in fruits:
    print("I like", fruit)

if "cherry" in fruits:
    print("Found it")
```

## Slices
```python
nums = [10, 20, 30, 40, 50]
print(nums[1:3])   # [20, 30]
print(nums[:2])    # [10, 20]
print(nums[2:])    # [30, 40, 50]
```

## Try it
1. Make a list of 5 friends and print each with a greeting.
2. Ask for 3 numbers, store them in a list, print the biggest and the total.
3. Print the list backwards (hint: `nums.reverse()` or `nums[::-1]`).
