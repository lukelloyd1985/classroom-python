# Lab 5: Shopping list (solution)
items = []

print("Type items to add. Type done when finished.")
while True:
    item = input("Item: ")
    if item == "done":
        break
    items.append(item)

items.sort()
print("You have " + str(len(items)) + " items:")
for i in range(len(items)):
    print(str(i + 1) + ". " + items[i])
