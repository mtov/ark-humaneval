from src.solution import triangle_area



METADATA = {}


def check(candidate):
    assert candidate(5, 3) == 7.5
    assert candidate(2, 2) == 2.0
    assert candidate(10, 8) == 40.0



def test_solution():
    check(triangle_area)
