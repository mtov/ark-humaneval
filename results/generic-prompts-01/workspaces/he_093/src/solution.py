
def encode(message):
    """
    Write a function that takes a message, and encodes in such a 
    way that it swaps case of all letters, replaces all vowels in 
    the message with the letter that appears 2 places ahead of that 
    vowel in the english alphabet. 
    Assume only letters. 
    
    Examples:
    >>> encode('test')
    'TGST'
    >>> encode('This is a message')
    'tHKS KS C MGSSCGG'
    """
    vowels = {'a': 'c', 'e': 'g', 'i': 'k', 'o': 'q', 'u': 'w'}
    encoded = []
    for char in message:
        swapped = char.swapcase()
        replacement = vowels.get(swapped.lower())
        if replacement:
            swapped = replacement.upper() if swapped.isupper() else replacement
        encoded.append(swapped)
    return ''.join(encoded)
