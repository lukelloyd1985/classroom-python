# Lab 4: Times tables (solution)
n = int(input("Which table? "))

for i in range(1, 13):
    print(str(n) + " x " + str(i) + " = " + str(n * i))

# Stretch 1
print("--- all tables ---")
for a in range(1, 13):
    for b in range(1, 13):
        print(a, "x", b, "=", a * b)
    print("")
