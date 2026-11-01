# Lab 7: Quiz (solution)
questions = {
    "What is the capital of France? ": "paris",
    "What is 6 x 7? ": "42",
    "What colour do you get from blue and yellow? ": "green",
    "How many days are in a week? ": "7",
}

score = 0
for question in questions:
    answer = input(question).lower()
    if answer == questions[question]:
        print("Correct!")
        score += 1
    else:
        print("Wrong. The answer was " + questions[question])

print("You got " + str(score) + " out of " + str(len(questions)))

if score == len(questions):
    print("Perfect!")
elif score >= len(questions) / 2:
    print("Well done!")
else:
    print("Keep practising!")
