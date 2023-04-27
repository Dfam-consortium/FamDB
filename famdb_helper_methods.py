import re

from famdb_globals import SOUNDEX_LOOKUP


def soundex(word):
    """
    Converts 'word' according to American Soundex[1].

    This is used for "sounds like" types of searches.

    [1]: https://en.wikipedia.org/wiki/Soundex#American_Soundex
    """

    codes = [SOUNDEX_LOOKUP[ch] for ch in word.upper() if ch in SOUNDEX_LOOKUP]

    # Start at the second code
    i = 1

    # Drop identical sounds and H and W
    while i < len(codes):
        code = codes[i]
        prev = codes[i - 1]

        if code is None:
            # Drop H and W
            del codes[i]
        elif code == prev:
            # Drop adjacent identical sounds
            del codes[i]
        else:
            i += 1

    # Keep the first letter
    coding = word[0]

    # Keep codes, except for the first or vowels
    codes_rest = filter(lambda c: c > 0, codes[1:])

    # Append stringified remaining numbers
    for code in codes_rest:
        coding += str(code)

    # Pad to 3 digits
    while len(coding) < 4:
        coding += "0"

    # Truncate to 3 digits
    return coding[:4]


def sounds_like(first, second):
    """
    Returns true if the string 'first' "sounds like" 'second'.

    The comparison is currently implemented by running both strings through the
    soundex algorithm and checking if the soundex values are equal.
    """
    soundex_first = soundex(first)
    soundex_second = soundex(second)

    return soundex_first == soundex_second


def sanitize_name(name):
    """
    Returns the "sanitized" version of the given 'name'.
    This must be kept in sync with Dfam's algorithm.
    """
    name = re.sub(r"[\s\,\_]+", "_", name)
    name = re.sub(r"[\(\)\<\>\']+", "", name)
    return name
