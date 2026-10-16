
def count_up_to(n):
    """Implement a function that takes an non-negative integer and returns an array of the first n
    integers that are prime numbers and less than n.
    for example:
    count_up_to(5) => [2,3]
    count_up_to(11) => [2,3,5,7]
    count_up_to(0) => []
    count_up_to(20) => [2,3,5,7,11,13,17,19]
    count_up_to(1) => []
    count_up_to(18) => [2,3,5,7,11,13,17]
    """
    if n <= 2:
        return []

    is_prime = [True] * n
    is_prime[0] = is_prime[1] = False

    for candidate in range(2, int(n ** 0.5) + 1):
        if is_prime[candidate]:
            for multiple in range(candidate * candidate, n, candidate):
                is_prime[multiple] = False

    return [number for number, prime in enumerate(is_prime) if prime]
