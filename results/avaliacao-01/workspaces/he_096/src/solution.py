
def count_up_to(n):
    """Return all prime numbers less than n."""
    if n <= 2:
        return []

    is_prime = [True] * n
    is_prime[0] = is_prime[1] = False

    for candidate in range(2, int(n ** 0.5) + 1):
        if is_prime[candidate]:
            for multiple in range(candidate * candidate, n, candidate):
                is_prime[multiple] = False

    return [number for number, prime in enumerate(is_prime) if prime]
