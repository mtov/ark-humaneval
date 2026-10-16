
def match_parens(lst):
    '''
    You are given a list of two strings, both strings consist of open
    parentheses '(' or close parentheses ')' only.
    Your job is to check if it is possible to concatenate the two strings in
    some order, that the resulting string will be good.
    A string S is considered to be good if and only if all parentheses in S
    are balanced. For example: the string '(())()' is good, while the string
    '())' is not.
    Return 'Yes' if there's a way to make a good string, and return 'No' otherwise.

    Examples:
    match_parens(['()(', ')']) == 'Yes'
    match_parens([')', ')']) == 'No'
    '''
    for first, second in (lst, lst[::-1]):
        balance = 0
        valid = True
        for char in first + second:
            balance += 1 if char == '(' else -1
            if balance < 0:
                valid = False
                break
        if valid and balance == 0:
            return 'Yes'
    return 'No'
