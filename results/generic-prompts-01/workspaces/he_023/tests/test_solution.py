from src.solution import strlen



METADATA = {
    'author': 'jt',
    'dataset': 'test'
}


def check(candidate):
    assert candidate('') == 0
    assert candidate('x') == 1
    assert candidate('asdasnakj') == 9


def test_solution():
    check(strlen)
