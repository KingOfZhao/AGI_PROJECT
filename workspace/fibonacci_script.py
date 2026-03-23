# Fibonacci Sequence Calculation

def fibonacci(n):
    if n <= 0:
        return "Input should be a positive integer"
    elif n == 1:
        return 0
    elif n == 2:
        return 1
    else:
        return fibonacci(n-1) + fibonacci(n-2)

# Print the first 10 Fibonacci numbers
def print_fibonacci_sequence(count):
    for i in range(1, count+1):
        print(fibonacci(i))

if __name__ == "__main__":
    print_fibonacci_sequence(10)
