import time

def performance_monitor(func):
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        print(f"Function {func.__name__} took {end_time - start_time:.4f} seconds to execute.")
        return result
    return wrapper

@performance_monitor
def example_function(n):
    total = 0
    for i in range(n):
        total += i
    return total

if __name__ == "__main__":
    result = example_function(1000000)
    print(f"Result: {result}")