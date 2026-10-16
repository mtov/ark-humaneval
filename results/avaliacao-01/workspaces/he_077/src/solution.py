
def iscube(a):
    '''
    Write a function that takes an integer a and returns True 
    if this ingeger is a cube of some integer number.
    Note: you may assume the input is always valid.
    Examples:
    iscube(1) ==> True
    iscube(2) ==> False
    iscube(-1) ==> True
    iscube(64) ==> True
    iscube(0) ==> True
    iscube(180) ==> False
    '''
    target = abs(a)
    low, high = 0, target

    while low <= high:
        mid = (low + high) // 2
        cube = mid ** 3
        if cube == target:
            return True
        if cube < target:
            low = mid + 1
        else:
            high = mid - 1

    return False
