# Lab 3: Number guesser (solution)
import random

secret = random.randint(1, 20)
guesses = 0

print("I am thinking of a number from 1 to 20.")
while True:
    guess = int(input("Your guess: "))
    guesses += 1

    if guess < secret:
        print("Too low")
    elif guess > secret:
        print("Too high")
    else:
        print("Correct! It took you " + str(guesses) + " guesses.")
        break
