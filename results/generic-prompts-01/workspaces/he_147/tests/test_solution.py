from src.solution import get_max_triples

def check(candidate):

    assert candidate(5) == 1
    assert candidate(6) == 4
    assert candidate(10) == 36
    assert candidate(100) == 53361


def test_solution():
    check(get_max_triples)
