
def is_nested(string):
    '''
    Create a function that takes a string as input which contains only square brackets.
    The function should return True if and only if there is a valid subsequence of brackets 
    where at least one bracket in the subsequence is nested.

    is_nested('[[]]') ➞ True
    is_nested('[]]]]]]][[[[[]') ➞ False
    is_nested('[][]') ➞ False
    is_nested('[]') ➞ False
    is_nested('[[][]]') ➞ True
    is_nested('[[]][[') ➞ True
    '''
    opening_brackets = 0
    closing_brackets_after_two_openings = 0

    for bracket in string:
        if bracket == '[':
            opening_brackets += 1
        elif opening_brackets >= 2:
            closing_brackets_after_two_openings += 1
            if closing_brackets_after_two_openings >= 2:
                return True

    return False
