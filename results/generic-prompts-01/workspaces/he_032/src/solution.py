import math


def poly(xs: list, x: float):
    """
    Evaluates polynomial with coefficients xs at point x.
    return xs[0] + xs[1] * x + xs[1] * x^2 + .... xs[n] * x^n
    """
    return sum([coeff * math.pow(x, i) for i, coeff in enumerate(xs)])


def find_zero(xs: list):
    """ xs are coefficients of a polynomial.
    find_zero find x such that poly(x) = 0.
    find_zero returns only only zero point, even if there are many.
    Moreover, find_zero only takes list xs having even number of coefficients
    and largest non zero coefficient as it guarantees
    a solution.
    >>> round(find_zero([1, 2]), 2) # f(x) = 1 + 2x
    -0.5
    >>> round(find_zero([-6, 11, -6, 1]), 2) # (x - 1) * (x - 2) * (x - 3) = -6 + 11x - 6x^2 + x^3
    1.0
    """
    radius = 1.0
    while True:
        left = -radius
        right = radius
        f_left = poly(xs, left)
        f_right = poly(xs, right)
        if f_left == 0:
            return left
        if f_right == 0:
            return right
        if (f_left < 0) != (f_right < 0):
            break
        radius *= 2.0

    for _ in range(100):
        middle = (left + right) / 2.0
        f_middle = poly(xs, middle)
        if f_middle == 0:
            return middle
        if (f_left < 0) != (f_middle < 0):
            right = middle
            f_right = f_middle
        else:
            left = middle
            f_left = f_middle

    return (left + right) / 2.0
