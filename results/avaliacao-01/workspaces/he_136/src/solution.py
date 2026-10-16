
def largest_smallest_integers(lst):
    '''
    Create a function that returns a tuple (a, b), where 'a' is
    the largest of negative integers, and 'b' is the smallest
    of positive integers in a list.
    If there is no negative or positive integers, return them as None.

    Examples:
    largest_smallest_integers([2, 4, 1, 3, 5, 7]) == (None, 1)
    largest_smallest_integers([]) == (None, None)
    largest_smallest_integers([0]) == (None, None)
    '''
    largest_negative = None
    smallest_positive = None

    for value in lst:
        if value < 0 and (largest_negative is None or value > largest_negative):
            largest_negative = value
        elif value > 0 and (smallest_positive is None or value < smallest_positive):
            smallest_positive = value

    return largest_negative, smallest_positive
