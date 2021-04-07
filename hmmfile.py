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

import logging
import re

import famdb

LOGGER = logging.getLogger(__name__)

def set_family_code(family, code, value, tax_db, taxid_lookup):
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
    elif code == "TH":
        match = re.match(r"TaxId:\s*(\d+);\s*TaxName:\s*.*;\s*GA:\s*([\.\d]+);\s*TC:\s*([\.\d]+);\s*NC:\s*([\.\d]+);\s*fdr:\s*([\.\d]+);", value)
        if match:
            tax_id = int(match.group(1))
            tax_db[tax_id].mark_ancestry_used()

            tc_value = float(match.group(3))
            if family.general_cutoff is None or family.general_cutoff < tc_value:
                family.general_cutoff = tc_value

            th_values = "{}, {}, {}, {}, {}".format(tax_id, match.group(2), match.group(3), match.group(4), match.group(5))
            if family.taxa_thresholds is None:
                family.taxa_thresholds = ""
            else:
                family.taxa_thresholds += "\n"
            family.taxa_thresholds += th_values
    elif code == "CT":
        family.classification = value
    elif code == "MS":
        match = re.match(r"TaxId:\s*(\d+)", value)
        if match:
            family.clades += [int(match.group(1))]
    elif code == "CC":
        matches = re.match(r'\s*Type:\s*(\S+)', value)
        if matches:
            family.repeat_type = matches.group(1).strip()

        matches = re.match(r'\s*SubType:\s*(\S+)', value)
        if matches:
            family.repeat_subtype = matches.group(1).strip()

        matches = re.search(r'Species:\s*(.+)', value)
        if matches:
            for spec in matches.group(1).split(","):
                name = spec.strip().lower()
                if name:
                    tax_id = taxid_lookup.get(name)
                    if tax_id:
                        if tax_id not in family.clades:
                            LOGGER.warning("MS line does not match RepeatMaksser Species: line in '%s'!", name)
                    else:
                        LOGGER.warning("Could not find taxon for '%s'", name)

        matches = re.search(r'SearchStages:\s*(\S+)', value)
        if matches:
            family.search_stages = matches.group(1).strip()

        matches = re.search(r'BufferStages:\s*(\S+)', value)
        if matches:
            family.buffer_stages = matches.group(1).strip()

        matches = re.search('Refineable', value)
        if matches:
            family.refineable = True

def iterate_hmm_file(file, tax_db, taxid_lookup):
    """Iterates over Family objects from the .hmm file 'file'."""
    family = None
    in_metadata = False
    model = None

    for line in file:
        if family is None:
            # HMMER3/f indicates start of metadata
            if line.startswith("HMMER3/f"):
                family = famdb.Family()
                family.clades = []
                in_metadata = True
                model = line
        else:
            if not(any(map(line.startswith, ["GA", "TC", "NC", "TH", "BM", "SM", "CT", "MS", "CC"]))):
                model += line

            if in_metadata:
                # HMM line indicates start of model
                if line.startswith("HMM"):
                    in_metadata = False

                # Continuing metadata
                else:
                    code = line[:6].strip()
                    value = line[6:].rstrip("\n")
                    set_family_code(family, code, value, tax_db, taxid_lookup)

            # '//' line indicates end of a model
            elif line.startswith("//"):
                family.model = model
                yield family
                family = None
