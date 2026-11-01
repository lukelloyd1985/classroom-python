# Lab 6: Temperature converter (solution)
def c_to_f(c):
    return c * 9 / 5 + 32

def f_to_c(f):
    return (f - 32) * 5 / 9

print(c_to_f(0))
print(c_to_f(100))
print(f_to_c(212))

# Stretch
value = float(input("Temperature: "))
direction = input("Convert to (F)ahrenheit or (C)elsius? ")
if direction == "F" or direction == "f":
    print(round(c_to_f(value), 1))
else:
    print(round(f_to_c(value), 1))
