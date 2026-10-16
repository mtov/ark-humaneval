
def is_multiply_prime(a):
    """Write a function that returns true if the given number is the multiplication of 3 prime numbers
    and false otherwise.
    Knowing that (a) is less then 100. 
    Example:
    is_multiply_prime(30) == True
    30 = 2 * 3 * 5
    """
    factor_count = 0
    divisor = 2

    while divisor * divisor <= a:
        while a % divisor == 0:
            factor_count += 1
            a //= divisor
            if factor_count > 3:
                return False
        divisor += 1

    if a > 1:
        factor_count += 1

    return factor_count == 3
