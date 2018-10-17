# -*- coding: utf-8 -*-
"""
    hmmfile.py

    Implements an iterator over Dfam-style .hmm files containing
    family metadata and models, yielding FamDB Family objects.

SEE ALSO:
    famdb.py
    Dfam: http://www.dfam.org

AUTHOR(S):
    Jeb Rosen <jeb.rosen@systemsbiology.org>

LICENSE:
    This code may be used in accordance with the Creative Commons
    Zero ("CC0") public domain dedication:
    https://creativecommons.org/publicdomain/zero/1.0/

DISCLAIMER:
    This software is provided ``AS IS'' and any express or implied
    warranties, including, but not limited to, the implied warranties of
    merchantability and fitness for a particular purpose, are disclaimed.
    In no event shall the authors or the Dfam consortium members be
    liable for any direct, indirect, incidental, special, exemplary, or
    consequential damages (including, but not limited to, procurement of
    substitute goods or services; loss of use, data, or profits; or
    business interruption) however caused and on any theory of liability,
    whether in contract, strict liability, or tort (including negligence
    or otherwise) arising in any way out of the use of this software, even
    if advised of the possibility of such damage.
"""

import re

import famdb


def set_family_code(family, code, value):
    """
    Sets an attribute on 'family' based on the hmm shortcode 'code'.
    For codes corresponding to list attributes, values are appended.
    """
    if code == "NAME":
        family.name = value
    elif code == "ACC":
        family.accession = value
    elif code == "DESC":
        family.description = value
    elif code == "LENG":
        family.length = int(value)
    elif code == "MS":
        match = re.match(r"TaxId:\s*(\d+)", value)
        if match:
            family.clades += [match.group(1)]

def iterate_hmm_file(file):
    """Iterates over Family objects from the .hmm file 'file'."""
    family = None
    in_metadata = False
    model = None

    for line in file:
        if family is None:
            # HMMER3/f indicates start of metadata
            if line.startswith("HMMER3/f"):
                family = famdb.Family()
                in_metadata = True
                model = line
        else:
            model += line
            if in_metadata:
                # HMM line indicates start of model
                if line.startswith("HMM"):
                    in_metadata = False

                # Continuing metadata
                else:
                    code = line[:6].strip()
                    value = line[6:].rstrip("\n")
                    set_family_code(family, code, value)

            # '//' line indicates end of a model
            elif line.startswith("//"):
                family.model = model
                yield family
                family = None
