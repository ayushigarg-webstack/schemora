def fibonacci(n: int) -> int:
    """Calculates the nth Fibonacci number recursively."""
    if n <= 0:
        return 0
    elif n == 1:
        return 1
    else:
        left = fibonacci(n - 1)
        right = fibonacci(n - 2)
        return left + right

# Example execution
fib_val = fibonacci(4)
