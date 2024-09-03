
import art
def add(n1, n2):
    return n1 + n2

def sub(n1, n2):
    return n1 - n2
def mul(n1, n2):
    return n1 * n2
def divide(n1, n2):
    return n1 / n2
operations = {"+": add,
              "-": sub,
              "*": mul,
              "/": divide
              }
# print(operations["*"](4,8))
def calculator():
    print(art.logo)
    should_operate= True
    num1 = float(input("enter first number:"))
    while should_operate:

        for symbol in operations:
              print(symbol)
        operations_symbol = input("enter symbol: ")
        num2 = float(input("enter second number: "))
        ans = operations[operations_symbol](num1, num2)
        print(f"{num1} {operations_symbol} {num2} = {ans}")

        choice = input(f"type 'y' to continue with {ans}, or type 'n' to start a new calculation: ")

        if choice == "y":
            num1 = ans
        else:
            should_operate = False
            print("\n" * 20)
            calculator()

calculator()
