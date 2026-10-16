

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
    def is_prime(value):
        if value < 2:
            return False
        if value % 2 == 0:
            return value == 2

        divisor = 3
        while divisor * divisor <= value:
            if value % divisor == 0:
                return False
            divisor += 2
        return True

    a, b = 0, 1
    count = 0
    while count < n:
        a, b = b, a + b
        if is_prime(a):
            count += 1
    return a
