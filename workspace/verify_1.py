import time

def simulate_page_load():
    # Simulate page load time
    time.sleep(2)
    return "Page loaded"

def optimize_performance(page_elements):
    # Optimize performance by reducing unnecessary elements or improving rendering
    optimized_elements = [element for element in page_elements if element['essential']]
    return optimized_elements

def main():
    start_time = time.time()
    
    # Simulate initial page load
    print(simulate_page_load())
    
    # Example page elements with an 'essential' flag
    page_elements = [
        {'name': 'Header', 'essential': True},
        {'name': 'Footer', 'essential': True},
        {'name': 'Ad Banner', 'essential': False},
        {'name': 'Sidebar', 'essential': False}
    ]
    
    # Optimize page elements
    optimized_page = optimize_performance(page_elements)
    print("Optimized Page Elements:", [element['name'] for element in optimized_page])
    
    end_time = time.time()
    print(f"Total time taken: {end_time - start_time:.2f} seconds")

if __name__ == "__main__":
    main()