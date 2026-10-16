
def strange_sort_list(lst):
    '''
    Given list of integers, return list in strange order.
    Strange sorting, is when you start with the minimum value,
    then maximum of the remaining integers, then minimum and so on.

    Examples:
    strange_sort_list([1, 2, 3, 4]) == [1, 4, 2, 3]
    strange_sort_list([5, 5, 5, 5]) == [5, 5, 5, 5]
    strange_sort_list([]) == []
    '''
    remaining = sorted(lst)
    result = []
    take_minimum = True

    while remaining:
        if take_minimum:
            result.append(remaining.pop(0))
        else:
            result.append(remaining.pop())
        take_minimum = not take_minimum

    return result
