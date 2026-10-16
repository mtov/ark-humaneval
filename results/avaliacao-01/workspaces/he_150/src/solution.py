
def x_or_y(n, x, y):
    """A simple program which should return the value of x if n is 
    a prime number and should return the value of y otherwise.

    Examples:
    for x_or_y(7, 34, 12) == 34
    for x_or_y(15, 8, 5) == 5
    
    """
    if n < 2:
        return y

    divisor = 2
    while divisor * divisor <= n:
        if n % divisor == 0:
            return y
        divisor += 1

    return x
