import sys
import time

def factorial_recursive(n):
    if n == 0:
        return 1
    else:
        return n * factorial_recursive(n - 1)

def factorial_iterative(n):
    result = 1
    for i in range(2, n + 1):
        result *= i
    return result

def main():
    n = 1000
    
    # Increase the recursion limit to allow deeper recursive calls
    sys.setrecursionlimit(3000)
    
    start_time = time.time()
    factorial_recursive(n)
    recursive_time = time.time() - start_time
    print(f"Recursive time: {recursive_time:.6f} seconds")
    
    start_time = time.time()
    factorial_iterative(n)
    iterative_time = time.time() - start_time
    print(f"Iterative time: {iterative_time:.6f} seconds")

if __name__ == "__main__":
    main()