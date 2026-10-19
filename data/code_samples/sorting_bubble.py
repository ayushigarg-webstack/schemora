def bubble_sort(arr: list) -> list:
    """Sorts a list in ascending order using bubble sort."""
    n = len(arr)
    sorted_arr = list(arr)
    
    for i in range(n):
        swapped = False
        for j in range(0, n - i - 1):
            if sorted_arr[j] > sorted_arr[j + 1]:
                temp = sorted_arr[j]
                sorted_arr[j] = sorted_arr[j + 1]
                sorted_arr[j + 1] = temp
                swapped = True
        if not swapped:
            break
            
    return sorted_arr

# Example execution
sorted_list = bubble_sort([5, 2, 8, 1, 9])
