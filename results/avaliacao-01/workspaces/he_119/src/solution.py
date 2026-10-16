
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
    def balance_info(s):
        balance = 0
        min_balance = 0
        for char in s:
            balance += 1 if char == '(' else -1
            min_balance = min(min_balance, balance)
        return balance, min_balance

    (balance_a, min_a), (balance_b, min_b) = map(balance_info, lst)

    for (first_balance, first_min), (second_balance, second_min) in (
        ((balance_a, min_a), (balance_b, min_b)),
        ((balance_b, min_b), (balance_a, min_a)),
    ):
        if (
            first_balance + second_balance == 0
            and first_min >= 0
            and first_balance + second_min >= 0
        ):
            return 'Yes'

    return 'No'
