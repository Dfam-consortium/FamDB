import logging

LOGGER = logging.getLogger(__name__)

# The current version of the file format
FILE_VERSION = "0.5"

LEAF_LINK = "leaf_link:"
ROOT_LINK = "root_link:"

# TODO: make command-line options to customize these
DESCRIPTION = (
    "Dfam - A database of transposable element (TE) sequence alignments and HMMs."
)

COPYRIGHT_TEXT = """Dfam - A database of transposable element (TE) sequence alignments and HMMs
Copyright (C) %s The Dfam consortium.

Release: Dfam_%s
Date   : %s

This database is free; you can redistribute it and/or modify it
as you wish, under the terms of the CC0 1.0 license, a
'no copyright' license:

The Dfam consortium has dedicated the work to the public domain, waiving
all rights to the work worldwide under copyright law, including all related
and neighboring rights, to the extent allowed by law.

You can copy, modify, distribute and perform the work, even for
commercial purposes, all without asking permission.
See Other Information below.


Other Information

o In no way are the patent or trademark rights of any person affected by
  CC0, nor are the rights that other persons may have in the work or in how
  the work is used, such as publicity or privacy rights.
o Makes no warranties about the work, and disclaims liability for all uses of the
  work, to the fullest extent permitted by applicable law.
o When using or citing the work, you should not imply endorsement by the Dfam consortium.

You may also obtain a copy of the CC0 license here:
http://creativecommons.org/publicdomain/zero/1.0/legalcode
"""
# Soundex codes
SOUNDEX_LOOKUP = {
    "A": 0,
    "E": 0,
    "I": 0,
    "O": 0,
    "U": 0,
    "Y": 0,
    "B": 1,
    "F": 1,
    "P": 1,
    "V": 1,
    "C": 2,
    "G": 2,
    "J": 2,
    "K": 2,
    "Q": 2,
    "S": 2,
    "X": 2,
    "Z": 2,
    "D": 3,
    "T": 3,
    "L": 4,
    "M": 5,
    "N": 5,
    "R": 6,
    "H": None,
    "W": None,
}
