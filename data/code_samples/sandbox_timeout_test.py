# Benchmark Python sample: Infinite loop designed to verify execution tracer timeout limit
def infinite_loop_counter():
    x = 0
    while True:
        x += 1
    return x

infinite_loop_counter()
