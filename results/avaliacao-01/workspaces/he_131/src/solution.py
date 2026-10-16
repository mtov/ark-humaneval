
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
    for digit in str(n):
        value = int(digit)
        if value % 2:
            product *= value
            found_odd = True
    return product if found_odd else 0
