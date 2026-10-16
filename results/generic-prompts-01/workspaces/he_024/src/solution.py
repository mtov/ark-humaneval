

def largest_divisor(n: int) -> int:
    """ For a given number n, find the largest number that divides n evenly, smaller than n
    >>> largest_divisor(15)
    5
    """
    divisor = 2
    while divisor * divisor <= n:
        if n % divisor == 0:
            return n // divisor
        divisor += 1
    return 1
