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
    def evaluate(x):
        value = 0
        for coeff in reversed(xs):
            value = value * x + coeff
        return value

    value_at_zero = evaluate(0)
    if value_at_zero == 0:
        return 0

    # An odd-degree polynomial has opposite signs at the two infinities.
    # Search on the side where its value must eventually differ from its
    # value at zero.
    leading = next(coeff for coeff in reversed(xs) if coeff != 0)
    search_right = (leading > 0) != (value_at_zero > 0)
    if search_right:
        left = 0
        right = 1
        while (evaluate(right) > 0) == (value_at_zero > 0):
            right *= 2
    else:
        right = 0
        left = -1
        while (evaluate(left) > 0) == (value_at_zero > 0):
            left *= 2

    left_value = evaluate(left)
    for _ in range(200):
        middle = (left + right) / 2
        if middle == left or middle == right:
            return middle
        middle_value = evaluate(middle)
        if abs(middle_value) < 1e-12:
            return middle
        if (left_value > 0) == (middle_value > 0):
            left = middle
            left_value = middle_value
        else:
            right = middle

    return (left + right) / 2
