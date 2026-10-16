
def digits(n):
    """Given a positive integer n, return the product of the odd digits.
    Return 0 if all digits are even.
    For example:
    digits(1)  == 1
    digits(4)  == 0
    digits(235) == 15
    """
    product = 1
    found_odd = False

    while n > 0:
        digit = n % 10
        if digit % 2 == 1:
            product *= digit
            found_odd = True
        n //= 10

    return product if found_odd else 0
