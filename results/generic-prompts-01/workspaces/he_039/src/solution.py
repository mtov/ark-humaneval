

def prime_fib(n: int):
    """
    prime_fib returns n-th number that is a Fibonacci number and it's also prime.
    >>> prime_fib(1)
    2
    >>> prime_fib(2)
    3
    >>> prime_fib(3)
    5
    >>> prime_fib(4)
    13
    >>> prime_fib(5)
    89
    """
    a, b = 0, 1
    count = 0

    while True:
        a, b = b, a + b
        if a < 2:
            continue

        is_prime = True
        divisor = 2
        while divisor * divisor <= a:
            if a % divisor == 0:
                is_prime = False
                break
            divisor += 1

        if is_prime:
            count += 1
            if count == n:
                return a
