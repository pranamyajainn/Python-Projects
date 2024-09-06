from random import randint
from art import logo
print(logo)
easy_level_turn = 10
hard_level_turn = 5

#Fuction to check users' guess against actual answer
def check_answer(user_guess, actual_answer, turns):
    """checks answers and retuirns thr number of turns remaining"""
    if user_guess > actual_answer:
        print("Too high.")
        return turns - 1
    elif user_guess < actual_answer:
        print("Too low.")
        return turns -1
    else:
        print(f"You got it! The answer was {actual_answer}")


#Function to set difficulty
def set_difficulty():
    level = input("Choose a difficulty. Type 'easy' or 'hard':  ")
    if level == "easy":
          return easy_level_turn
    else:
        return hard_level_turn


#choosing random number between 1 and 100

print("Welcome to guessing game!")
def game():

    print("I'm thinking of a number between 1 and 100")
    answer = randint(1, 100)




    #Let the user guess a number

    turns = set_difficulty()


    guess =0
    while guess != answer:
          print(f"You have {turns} attempts remaining to guess the number.")
          guess = int(input("Make a guess: "))

          turns = check_answer(guess, answer, turns)
          if turns == 0:
              print("you've run out of guesses, you lose.")
              print(f"the correct answer was: {answer}")
              return
          elif guess != answer:
              print("Guess again.")




game()
    
