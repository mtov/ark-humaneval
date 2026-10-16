
def do_algebra(operator, operand):
    """
    Given two lists operator, and operand. The first list has basic algebra operations, and 
    the second list is a list of integers. Use the two given lists to build the algebric 
    expression and return the evaluation of this expression.

    The basic algebra operations:
    Addition ( + ) 
    Subtraction ( - ) 
    Multiplication ( * ) 
    Floor division ( // ) 
    Exponentiation ( ** ) 

    Example:
    operator['+', '*', '-']
    array = [2, 3, 4, 5]
    result = 2 + 3 * 4 - 5
    => result = 9

    Note:
        The length of operator list is equal to the length of operand list minus one.
        Operand is a list of of non-negative integers.
        Operator list has at least one operator, and operand list has at least two operands.

    """
    precedence = {"+": 1, "-": 1, "*": 2, "//": 2, "**": 3}
    operations = {
        "+": lambda left, right: left + right,
        "-": lambda left, right: left - right,
        "*": lambda left, right: left * right,
        "//": lambda left, right: left // right,
        "**": lambda left, right: left ** right,
    }

    values = [operand[0]]
    operators = []

    def apply_operator():
        operator = operators.pop()
        right = values.pop()
        left = values.pop()
        values.append(operations[operator](left, right))

    for operator, value in zip(operator, operand[1:]):
        while operators and (
            precedence[operators[-1]] > precedence[operator]
            or (
                precedence[operators[-1]] == precedence[operator]
                and operator != "**"
            )
        ):
            apply_operator()
        operators.append(operator)
        values.append(value)

    while operators:
        apply_operator()

    return values[0]
