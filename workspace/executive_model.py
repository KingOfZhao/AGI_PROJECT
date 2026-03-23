import random

class StepExecutionModel:
    def __init__(self, steps):
        self.steps = steps

    def execute(self):
        for step in self.steps:
            print(f"Executing step: {step}")
            # Simulate some work being done
            result = random.choice([True, False])
            if not result:
                print("Step failed")
                return False
        print("All steps completed successfully")
        return True

def main():
    steps = [
        "Initialize system",
        "Load data",
        "Process data",
        "Save results"
    ]
    
    model = StepExecutionModel(steps)
    success = model.execute()
    print(f"Execution successful: {success}")

if __name__ == "__main__":
    main()