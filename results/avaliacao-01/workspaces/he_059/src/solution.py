

def largest_prime_factor(n: int):
    """Return the largest prime factor of n. Assume n > 1 and is not a prime.
    >>> largest_prime_factor(13195)
    29
    >>> largest_prime_factor(2048)
    2
    """
    factor = 2
    largest = 1
    while factor * factor <= n:
        while n % factor == 0:
            largest = factor
            n //= factor
        factor += 1
    return n if n > 1 else largest
