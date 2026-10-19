def collatz_conjecture_steps(n: int) -> list:
    """Computes the Collatz sequence until reaching 1."""
    sequence = [n]
    current = n
    
    while current > 1:
        if current % 2 == 0:
            current = current // 2
        else:
            current = 3 * current + 1
        sequence.append(current)
        
    return sequence

# Example execution
steps = collatz_conjecture_steps(6)
