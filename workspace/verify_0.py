import time
from functools import wraps

def timing_decorator(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        print(f"Function {func.__name__} took {end_time - start_time:.4f} seconds to execute.")
        return result
    return wrapper

@timing_decorator
def example_function(n):
    total = 0
    for i in range(n):
        total += i
    return total

def main():
    result = example_function(1000000)
    print(f"Result of the function: {result}")

if __name__ == "__main__":
    main()