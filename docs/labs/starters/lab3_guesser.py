# Lab 3: Number guesser
# Goal: the computer picks a secret number; the player keeps guessing.

secret = 7          # TODO (stretch): make this random, see bottom of file
guesses = 0

while True:
    # TODO 1: ask for a guess and convert it to an int


    guesses += 1

    # TODO 2: if the guess is too low, print "Too low"
    #         if too high, print "Too high"
    #         if correct, print how many guesses it took and break


# Stretch (Pi mode and Tablet mode both support random):
#   import random
#   secret = random.randint(1, 20)
