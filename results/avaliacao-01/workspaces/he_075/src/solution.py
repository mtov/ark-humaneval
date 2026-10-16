
def is_multiply_prime(a):
    """Write a function that returns true if the given number is the multiplication of 3 prime numbers
    and false otherwise.
    Knowing that (a) is less then 100. 
    Example:
    is_multiply_prime(30) == True
    30 = 2 * 3 * 5
    """
    if a < 2:
        return False

    prime_factor_count = 0
    divisor = 2

    while divisor * divisor <= a:
        while a % divisor == 0:
            a //= divisor
            prime_factor_count += 1
        divisor += 1

    if a > 1:
        prime_factor_count += 1

    return prime_factor_count == 3
