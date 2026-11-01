# Lab 2: Tip calculator (solution)
bill = float(input("Bill amount: "))
percent = float(input("Tip percentage: "))

tip = bill * percent / 100
total = bill + tip

print("Tip:", round(tip, 2))
print("Total:", round(total, 2))

# Stretch
people = int(input("How many people? "))
print("Each person pays:", round(total / people, 2))
