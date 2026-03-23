class DataStructureManager:
    def __init__(self):
        self.data = {}

    def add_data(self, key, value):
        if not isinstance(key, str):
            raise ValueError("Key must be a string")
        if key in self.data:
            raise KeyError(f"Key '{key}' already exists")
        self.data[key] = value

    def get_data(self, key):
        try:
            return self.data[key]
        except KeyError as e:
            print(e)
            return None

    def remove_data(self, key):
        if key not in self.data:
            raise KeyError(f"Key '{key}' does not exist")
        del self.data[key]

def main():
    manager = DataStructureManager()
    
    try:
        manager.add_data("name", "Alice")
        print(manager.get_data("name"))  # Should print Alice
        manager.remove_data("name")
        print(manager.get_data("name"))  # Should print Key 'name' does not exist and None
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()