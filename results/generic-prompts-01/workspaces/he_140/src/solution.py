
def fix_spaces(text):
    """
    Given a string text, replace all spaces in it with underscores, 
    and if a string has more than 2 consecutive spaces, 
    then replace all consecutive spaces with - 
    
    fix_spaces("Example") == "Example"
    fix_spaces("Example 1") == "Example_1"
    fix_spaces(" Example 2") == "_Example_2"
    fix_spaces(" Example   3") == "_Example-3"
    """
    result = []
    index = 0
    while index < len(text):
        if text[index] == " ":
            end = index
            while end < len(text) and text[end] == " ":
                end += 1
            result.append("-" if end - index > 2 else "_" * (end - index))
            index = end
        else:
            result.append(text[index])
            index += 1
    return "".join(result)
