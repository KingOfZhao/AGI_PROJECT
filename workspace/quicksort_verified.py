def quicksort(arr):
    global recursion_count
    if len(arr) <= 1:
        return arr
    pivot = arr[len(arr) // 2]
    left = [x for x in arr if x < pivot]
    middle = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]
    recursion_count += 1
    return quicksort(left) + middle + quicksort(right)

if __name__ == "__main__":
    recursion_count = 0
    unsorted_list = [38, 27, 43, 3, 9, 82, 10]
    sorted_list = quicksort(unsorted_list)
    print("Sorted list:", sorted_list)
    print("Recursion calls:", recursion_count)