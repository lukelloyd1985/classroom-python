# 08 Dictionaries

A dictionary stores **key: value** pairs, like a real dictionary.

```python
pet = {"name": "Biscuit", "type": "dog", "age": 4}
print(pet["name"])
pet["age"] = 5               # change a value
pet["colour"] = "brown"      # add a new pair
```

## Safe lookup
```python
print(pet.get("owner", "unknown"))   # no crash if the key is missing
if "name" in pet:
    print("has a name")
```

## Looping
```python
for key in pet:
    print(key, "=", pet[key])
```

## Counting example
```python
text = "banana"
counts = {}
for letter in text:
    if letter in counts:
        counts[letter] += 1
    else:
        counts[letter] = 1
print(counts)
```

## Try it
1. Make a dictionary of 3 countries and their capitals; ask the user for a country and print the capital.
2. Count how many times each word appears in a sentence (hint: `sentence.split()`).
