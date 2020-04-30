#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
    famdb.py
    Usage: famdb.py [-h] [-l LOG_LEVEL] command ...


    This module provides classes and methods for working with FamDB files,
    which contain Transposable Element (TE) families and associated taxonomy data.

    # Classes
        Family: Metadata and model of a TE family.
        FamDB: HDF5-based format for storing Family objects.


SEE ALSO:
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

import argparse
import collections
import datetime
import json
import logging
import re
import textwrap
import time

import h5py
import numpy


LOGGER = logging.getLogger(__name__)


# Soundex codes
SOUNDEX_LOOKUP = {
    'A': 0, 'E': 0, 'I': 0, 'O': 0, 'U': 0, 'Y': 0,
    'B': 1, 'F': 1, 'P': 1, 'V': 1,
    'C': 2, 'G': 2, 'J': 2, 'K': 2, 'Q': 2, 'S': 2, 'X': 2, 'Z': 2,
    'D': 3, 'T': 3,
    'L': 4,
    'M': 5, 'N': 5,
    'R': 6,
    'H': None, 'W': None,
}

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
        prev = codes[i-1]

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
        coding += '0'

    # Truncate to 3 digits
    return coding[:4]

def sounds_like(first, second):
    soundex_first = soundex(first)
    soundex_second = soundex(second)

    return soundex_first == soundex_second

class Family:  # pylint: disable=too-many-instance-attributes
    """A Transposable Element family, made up of metadata and a model."""

    FamilyField = collections.namedtuple("FamilyField", ["name", "type"])

    # Known metadata fields
    META_FIELDS = [
        # Core required family metadata
        FamilyField("name", str),
        FamilyField("accession", str),
        FamilyField("version", int),
        FamilyField("consensus", str),
        FamilyField("length", int),

        # Optional family metadata
        FamilyField("title", str),
        FamilyField("author", str),
        FamilyField("description", str),
        FamilyField("classification", str),
        FamilyField("classification_note", str),
        FamilyField("search_stages", str),
        FamilyField("buffer_stages", str),
        FamilyField("clades", list),
        FamilyField("date_created", str),
        FamilyField("date_modified", str),
        FamilyField("repeat_type", str),
        FamilyField("repeat_subtype", str),
        FamilyField("features", str),
        FamilyField("coding_sequences", str),
        FamilyField("aliases", str),
        FamilyField("citations", str),
        FamilyField("refineable", bool),
        FamilyField("target_site_cons", str),

        # Metadata available when a model is present
        FamilyField("model", str),
        FamilyField("max_length", int),
        FamilyField("is_model_masked", bool),
        FamilyField("seed_count", int),
        FamilyField("build_method", str),
        FamilyField("search_method", str),
        FamilyField("taxa_thresholds", str),
        FamilyField("general_cutoff", float),
    ]

    # Metadata lookup by field name
    META_LOOKUP = {field.name: field for field in META_FIELDS}

    @staticmethod
    def type_for(name):
        """Returns the expected data type for the attribute 'name'."""
        return Family.META_LOOKUP[name].type

    def __getattr__(self, name):
        if name not in Family.META_LOOKUP:
            raise AttributeError("Unknown Family metadata attribute '{}'".format(name))

    def __setattr__(self, name, value):
        if name in Family.META_LOOKUP:
            expected_type = self.type_for(name)
            if value is not None and not isinstance(value, expected_type):
                try:
                    value = expected_type(value)
                except Exception as exc:
                    raise TypeError("Incompatible type for '{}'. Expected '{}', got '{}'".format(
                        name, expected_type, type(value))) from exc
            super().__setattr__(name, value)
        else:
            raise AttributeError("Unknown Family metadata attribute '{}'".format(name))

    def __str__(self):
        return "%s.%d '%s': %s len=%d" % (self.accession, self.version or 0,
                                          self.name, self.classification, self.length or -1)

    def to_dfam_hmm(self, famdb, species=None):  # pylint: disable=too-many-locals,too-many-branches
        """
        Converts 'self' to Dfam-style HMM format.
        'famdb' is required for further taxonomy lookups.
        If 'species' is given, the GA/TC/NC thresholds will be set to the
        assembly-specific thresholds.
        """
        if self.model is None:
            return None

        out = ""

        def append(tag, text, wrap=False):
            nonlocal out
            if not text:
                return

            prefix = "%-6s" % tag
            text = str(text)
            if wrap:
                text = textwrap.fill(text, width=72)
            out += textwrap.indent(text, prefix)
            out += "\n"

        model_lines = self.model.split("\n")

        i = 0
        for i, line in enumerate(model_lines):
            if line.startswith("HMMER3"):
                out += line + "\n"
                append("NAME", self.name)
                append("ACC", "%s.%d" % (self.accession, self.version or 0))
                append("DESC", self.title)
            elif any(map(line.startswith, ["NAME", "ACC", "DESC"])):
                # Correct version of this line was output already
                pass
            elif line.startswith("CKSUM"):
                out += line + "\n"
                break
            else:
                out += line + "\n"

        th_lines = []
        species_hmm_ga = None
        species_hmm_tc = None
        species_hmm_nc = None
        if self.taxa_thresholds:
            for threshold in self.taxa_thresholds.split("\n"):
                parts = threshold.split(",")
                tax_id = int(parts[0])
                (hmm_ga, hmm_tc, hmm_nc, hmm_fdr) = map(float, parts[1:])

                tax_name = famdb.get_taxon_name(tax_id, 'scientific name')
                if tax_id == species:
                    species_hmm_ga, species_hmm_tc, species_hmm_nc = hmm_ga, hmm_tc, hmm_nc
                th_lines += ["TaxId:%d; TaxName:%s; GA:%.2f; TC:%.2f; NC:%.2f; fdr:%.3f;" % (
                    tax_id, tax_name, hmm_ga, hmm_tc, hmm_nc, hmm_fdr)]

        if not species and self.general_cutoff:
            species_hmm_ga = species_hmm_tc = species_hmm_nc = self.general_cutoff

        if species_hmm_ga:
            append("GA", "%.2f;" % species_hmm_ga)
            append("TC", "%.2f;" % species_hmm_tc)
            append("NC", "%.2f;" % species_hmm_nc)

        for th_line in th_lines:
            append("TH", th_line)

        if self.build_method:
            append("BM", self.build_method)
        if self.search_method:
            append("SM", self.search_method)

        append("CT", self.classification.replace("root;", ""))

        for clade_id in self.clades:
            tax_name = famdb.get_taxon_name(clade_id, 'dfam sanitized name')
            append("MS", "TaxId:%d TaxName:%s" % (clade_id, tax_name))

        append("CC", self.description, True)
        append("CC", "RepeatMasker Annotations:")
        append("CC", "     Type: %s" % (self.repeat_type or ""))
        append("CC", "     SubType: %s" % (self.repeat_subtype or ""))

        species_names = [famdb.get_taxon_name(c, 'dfam sanitized name') for c in self.clades]
        append("CC", "     Species: %s" % ", ".join(species_names))

        append("CC", "     SearchStages: %s" % (self.search_stages or ""))
        append("CC", "     BufferStages: %s" % (self.buffer_stages or ""))

        if self.refineable:
            append("CC", "     Refineable")

        # Append all remaining lines unchanged
        out += "\n".join(model_lines[i+1:])

        return out

    def to_fasta(self, famdb, use_accession=False):
        """Converts 'self' to FASTA format."""
        sequence = self.consensus
        if sequence is None:
            return None

        if use_accession:
            identifier = "%s.%d" % (self.accession, self.version)
        else:
            identifier = self.name

        header = ">%s#%s/%s" % (identifier, self.repeat_type, self.repeat_subtype)

        for clade_id in self.clades:
            clade_name = famdb.get_taxon_name(clade_id, 'dfam sanitized name')
            header += " @" + clade_name

        if self.search_stages:
            header += " [S:%s]" % self.search_stages

        out = header + "\n"

        i = 0
        while i < len(sequence):
            out += sequence[i:i+60] + "\n"
            i += 60

        return out

    def to_embl(self, famdb, include_meta=True, include_seq=True):  # pylint: disable=too-many-locals,too-many-branches,too-many-statements
        """Converts 'self' to EMBL format."""

        sequence = self.consensus
        if sequence is None:
            return None

        out = ""

        def append(tag, text, wrap=False):
            nonlocal out
            if not text:
                return

            prefix = "%-5s" % tag
            if wrap:
                text = textwrap.fill(str(text), width=72)
            out += textwrap.indent(str(text), prefix)
            out += "\n"

        def append_featuredata(text):
            nonlocal out
            prefix = "FT                   "
            if text:
                out += textwrap.indent(textwrap.fill(str(text), width=72), prefix)
            out += "\n"

        append("ID", "%s; SV %d; linear; DNA; STD; UNC; %d BP." %
               (self.accession, self.version or 0, len(sequence)))
        append("NM", self.name)
        out += "XX\n"
        append("AC", self.accession + ';')
        out += "XX\n"
        append("DE", self.title, True)
        out += "XX\n"

        if include_meta:
            repbase_aliases = []
            if self.aliases:
                for alias_line in self.aliases.splitlines():
                    [db_id, db_link] = map(str.strip, alias_line.split(":"))
                    if db_id == "Repbase":
                        repbase_aliases += [db_link]
            for alias in repbase_aliases:
                append("DR", "Repbase; %s." % alias)
                out += "XX\n"

            if self.repeat_type == "LTR":
                append("KW", "Long terminal repeat of retrovirus-like element; %s." % self.name)
            else:
                append("KW", "%s/%s." % (self.repeat_type or "", self.repeat_subtype or ""))
            out += "XX\n"

            for clade_id in self.clades:
                lineage = famdb.get_lineage_name(clade_id).replace("root;", "")
                last_semi = lineage.rfind(';')
                append("OS", lineage[last_semi+1:])
                append("OC", lineage[:last_semi].replace(";", "; ") + ".", True)
            out += "XX\n"

            if self.citations:
                citations = json.loads(self.citations)
                citations.sort(key=lambda c: c["order_added"])
                for cit in citations:
                    append("RN", "[%d] (bases 1 to %d)" % (cit["order_added"], self.length))
                    append("RA", cit["authors"], True)
                    append("RT", cit["title"], True)
                    append("RL", cit["journal"])
                    out += "XX\n"

            append("CC", self.description, True)
            out += "CC\n"
            append("CC", "RepeatMasker Annotations:")
            append("CC", "     Type: %s" % (self.repeat_type or ""))
            append("CC", "     SubType: %s" % (self.repeat_subtype or ""))

            species_names = [famdb.get_taxon_name(c, 'dfam sanitized name')
                             for c in self.clades]
            append("CC", "     Species: %s" % ", ".join(species_names))

            append("CC", "     SearchStages: %s" % (self.search_stages or ""))
            append("CC", "     BufferStages: %s" % (self.buffer_stages or ""))
            if self.refineable:
                append("CC", "     Refineable")

            if self.coding_sequences:
                out += "XX\n"
                append("FH", "Key             Location/Qualifiers")
                out += "FH\n"
                for cds in json.loads(self.coding_sequences):
                    # TODO: sanitize values which might already contain a " in them?

                    append("FT", "CDS             %d..%d" % (cds["cds_start"], cds["cds_end"]))
                    append_featuredata('/product="%s"' % cds["product"])
                    append_featuredata('/number=%s' % cds["exon_count"])
                    append_featuredata('/note="%s"' % cds["description"])
                    append_featuredata('/translation="%s"' % cds["translation"])


            out += "XX\n"

        if include_seq:
            sequence = sequence.lower()
            i = 0
            counts = {"a": 0, "c": 0, "g": 0, "t": 0, "other": 0}
            for char in sequence:
                if char not in counts:
                    char = "other"
                counts[char] += 1

            append("SQ", "Sequence %d BP; %d A; %d C; %d G; %d T; %d other;" % (
                len(sequence), counts["a"], counts["c"], counts["g"], counts["t"],
                counts["other"]))

            while i < len(sequence):
                chunk = sequence[i:i+60]
                i += 60

                j = 0
                line = ""
                while j < len(chunk):
                    line += chunk[j:j + 10] + " "
                    j += 10

                out += "     %-66s %d\n" % (line, min(i, len(sequence)))

        out += "//\n"

        return out


class FamDB:
    """Transposable Element Family and taxonomy database."""

    dtype_str = h5py.special_dtype(vlen=str)

    def __init__(self, filename, mode="r"):
        if mode not in ["r", "w"]:
            raise ValueError("Invalid file mode. Expected 'r' or 'w', got '{}'".format(mode))

        self.file = h5py.File(filename, mode)
        self.mode = mode

        self.group_nodes = self.file.require_group("Taxonomy/Nodes")
        self.group_families = self.file.require_group("Families")
        self.group_byname = self.file.require_group("Families/ByName")
        self.group_byaccession = self.file.require_group("Families/ByAccession")

        if self.mode == "w":
            self.seen = {}
            self.__write_metadata()

    def __write_metadata(self):
        self.file.attrs["generator"] = "famdb.py v0.1"
        self.file.attrs["version"] = "0.1"
        self.file.attrs["created"] = str(datetime.datetime.now())

    def set_db_info(self, name, version, date, copyright_text):
        """Sets database metadata for the current file"""
        self.file.attrs["db_name"] = name
        self.file.attrs["db_version"] = version
        self.file.attrs["db_date"] = date
        self.file.attrs["db_copyright"] = copyright_text

    def get_db_info(self):
        """
        Gets database metadata for the current file as a dict with keys
        'name', 'version', 'date', 'copyright'
        """
        if "db_name" not in self.file.attrs:
            return None

        return {
            "name": self.file.attrs["db_name"],
            "version": self.file.attrs["db_version"],
            "date": self.file.attrs["db_date"],
            "copyright": self.file.attrs["db_copyright"],
        }

    def close(self):
        """Closes this FamDB instance, making further use invalid."""
        self.file.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def __check_unique(self, family, key):
        """Verifies that 'family' is uniquely identified by its value of 'key'."""

        seen = self.seen
        value = getattr(family, key)
        if key in seen:
            if value in seen[key]:
                raise Exception("Family is not unique! Already seen {}: {}".format(key, value))
            else:
                seen[key] += [value]
        else:
            seen[key] = [value]

    def add_family(self, family):
        """Adds the family described by 'family' to the database."""
        # Verify uniqueness of name and accession.
        # This is important because of the links created to them later.
        if family.name:
            self.__check_unique(family, "name")
        self.__check_unique(family, "accession")

        # Create the family data
        dset = self.group_families.create_dataset(family.accession, (0,))

        # Set the family attributes
        for k in Family.META_LOOKUP:
            value = getattr(family, k)
            if value:
                dset.attrs[k] = value

        # Create links
        if family.name:
            self.group_byname[family.name] = h5py.SoftLink("/Families/" + family.accession)
        self.group_byaccession[family.accession] = h5py.SoftLink("/Families/" + family.accession)

        LOGGER.debug("Added family %s (%s)", family.name, family.accession)

    def write_taxonomy(self, tax_db):
        """Writes taxonomy nodes in 'tax_db' to the database."""
        LOGGER.info("Writing taxonomy nodes to database")
        start = time.perf_counter()

        count = 0
        for taxon in tax_db.values():
            if taxon.used:
                count += 1

                taxon_group = self.group_nodes.require_group(str(taxon.tax_id))

                data = numpy.array(taxon.names)
                dset = taxon_group.create_dataset("Names", shape=data.shape,
                                                  dtype=FamDB.dtype_str)
                dset[:] = data

                families_group = taxon_group.require_group("Families")
                for family in taxon.families:
                    families_group[family] = h5py.SoftLink("/Families/" + family)

        def store_tree_links(taxon, parent_id):
            group = self.group_nodes[str(taxon.tax_id)]
            if parent_id:
                group.create_dataset("Parent", data=[parent_id])

            child_ids = []
            for child in taxon.children:
                if child.used:
                    child_ids += [child.tax_id]
                    store_tree_links(child, taxon.tax_id)

            group.create_dataset("Children", data=child_ids)

        LOGGER.info("Writing taxonomy tree")
        # 1 is the "root" taxon
        store_tree_links(tax_db[1], None)

        delta = time.perf_counter() - start
        LOGGER.info("Wrote %d taxonomy nodes in %f", count, delta)

    def has_taxon(self, tax_id):
        """Returns True if 'self' has a taxonomy entry for 'tax_id'"""
        return str(tax_id) in self.group_nodes

    def search_taxon_names(self, text, kind=None, search_similar=False):
        """
        Searches 'self' for taxons with a name containing 'text' and yields the
        ids of matching nodes.

        If 'similar' is True, names that sound similar will also be considered eligible.

        A list of strings may be passed as 'kind' to
        restrict what kinds of names will be searched.
        """

        text = text.lower()

        for nid in self.group_nodes:
            names = self.group_nodes[nid]["Names"]
            for name in names:
                if kind is None or kind == name[0]:
                    if text in name[1].lower():
                        yield int(nid)
                        break
                    elif search_similar and sounds_like(text, name[1].lower()):
                        yield int(nid)
                        break

    def resolve_species(self, term, kind=None, search_similar=False):
        """
        Resolves 'term' as a species or clade in 'self'. If 'term' is a number,
        it is a taxon id. Otherwise, it will be searched for in 'self' in the
        name fields of all taxa. A list of strings may be passed as 'kind' to
        restrict what kinds of names will be searched.

        If 'search_similar' is True, a "sounds like" search
        will be tried first. If it is False, a "sounds like"
        will be performed and printed to the screen but no
        results will be returned.

        This function returns a list of taxon ids that match the query. The list
        will be empty if no matches were found.
        """

        # Try as a number
        try:
            tax_id = int(term)
            if self.has_taxon(tax_id):
                return [tax_id]

            return []
        except ValueError:
            pass

        # Perform a search by name
        results = list(self.search_taxon_names(term, kind, search_similar))

        if len(results) == 0 and not search_similar:
            # Try a sounds-like search (currently soundex)
            similar_results = self.resolve_species(term, kind, True)
            if similar_results:
                print("No results found by that name, but some names sound similar:")
                for tax_id in similar_results:
                    names = self.get_taxon_names(tax_id)
                    print(tax_id, ", ".join(["{1}".format(*n) for n in names]))

        return results

    def resolve_one_species(self, term, kind=None):
        """
        Resolves 'term' in 'dbfile' as a taxon id or search term unambiguously.
        Parameters are as in the 'resolve_species' method.
        Raises an exception if not exactly one result is found.
        """

        results = self.resolve_species(term, kind)
        if len(results) == 1:
            return results[0]

        raise Exception("Ambiguous search term '{}' (found {} results)".format(term, len(results)))

    def get_taxon_names(self, tax_id):
        """
        Returns a list of [name_class, name_value] of the taxon given by 'tax_id'.
        """

        names = self.group_nodes[str(tax_id)]["Names"]
        return names[:, :]

    def get_taxon_name(self, tax_id, kind='scientific name'):
        """
        Returns the first name of the given 'kind' for the taxon given by 'tax_id',
        or None if no such name was found.
        """

        names = self.group_nodes[str(tax_id)]["Names"]
        for name in names:
            if name[0] == kind:
                return name[1]

        return None

    def get_families_for_taxon(self, tax_id):
        """Returns a list of the accessions for each family directly associated with 'tax_id'."""
        return self.group_nodes[str(tax_id)]["Families"].keys()

    def get_lineage(self, tax_id, **kwargs):
        """
        Returns the lineage of 'tax_id'. Recognized kwargs: 'descendants' to include
        descendant taxa, 'ancestors' to include ancestor taxa.
        IDs are returned as a nested list, for example
        [ 1, [ 2, [3, [4]], [5], [6, [7]] ] ]
        where '2' may have been the passed in 'tax_id'.
        """
        if kwargs.get("descendants"):
            def descendants_of(tax_id):
                descendants = [int(tax_id)]
                for child in self.group_nodes[str(tax_id)]["Children"]:
                    descendants += [descendants_of(child)]
                return descendants
            tree = descendants_of(tax_id)
        else:
            tree = [tax_id]

        if kwargs.get("ancestors"):
            while tax_id:
                node = self.group_nodes[str(tax_id)]
                if "Parent" in node:
                    tax_id = node["Parent"][0]
                    tree = [tax_id, tree]
                else:
                    tax_id = None

        return tree

    def get_lineage_name(self, tax_id):
        """
        Returns a ';'-separated string of the lineage for 'tax_id'.
        """

        tree = self.get_lineage(tax_id, ancestors=True)
        lineage = ""

        while tree:
            node = tree[0]
            tree = tree[1] if len(tree) > 1 else None

            tax_name = self.get_taxon_name(node, 'scientific name')
            lineage += tax_name
            if tree:
                lineage += ';'

        return lineage


    def get_accessions_filtered(self, **kwargs):
        """
        Yields accessions for the families requested.

        Filters are specified in kwargs:
            tax_id: int
            ancestors: boolean, default False
            descendants: boolean, default False
                If none of (tax_id, ancestors, descendants) are
                specified, *all* families will be checked.
            stage = int
            repeat_type = string (prefix)
            name = string (prefix)
                If any of stage, repeat_type, or name are
                omitted (or None), they will not be used to filter.
        """

        if not ("tax_id" in kwargs or "ancestors" in kwargs or "descendants" in kwargs):
            tax_id = 1
            ancestors = True
            descendants = True
        else:
            tax_id = kwargs["tax_id"]
            ancestors = kwargs["ancestors"] or False
            descendants = kwargs["descendants"] or False

        filter_stage = kwargs.get("stage")
        if filter_stage:
            filter_stage = str(filter_stage)

        filter_repeat_type = kwargs.get("repeat_type")
        if filter_repeat_type:
            filter_repeat_type = filter_repeat_type.lower()

        filter_name = kwargs.get("name")
        if filter_name:
            filter_name = filter_name.lower()

        seen = set()
        for node in walk_tree(self.get_lineage(tax_id, ancestors=ancestors, descendants=descendants)):
            for accession in self.get_families_for_taxon(node):
                if accession not in seen:
                    seen.add(accession)
                    family = self.__get_family_raw_by_accession(accession)
                    if filter_stage:
                        match_stage = False
                        if family.attrs.get("search_stages"):
                            for sstage in family.attrs["search_stages"].split(","):
                                if sstage.strip() == filter_stage:
                                    match_stage = True
                        if family.attrs.get("buffer_stages"):
                            for bstage in family.attrs["buffer_stages"].split(","):
                                if bstage == filter_stage:
                                    match_stage = True
                                elif "[" in bstage:
                                    if bstage.split("[")[0] == filter_stage:
                                        match_stage = True
                        if not match_stage:
                            continue

                    if filter_repeat_type:
                        match_class = False
                        if family.attrs.get("repeat_type"):
                            if family.attrs["repeat_type"].lower().startswith(filter_repeat_type):
                                match_class = True
                        if not match_class:
                            continue

                    if filter_name:
                        match_name = False
                        if family.attrs.get("name"):
                            if family.attrs["name"].lower().startswith(filter_name):
                                match_name = True
                        if not match_name:
                            continue

                    yield accession

    def get_family_names(self):
        """Returns a list of names of families in the database."""
        return sorted(self.group_byname.keys(), key=str.lower)

    def get_family_accessions(self):
        """Returns a list of accessions for families in the database."""
        return sorted(self.group_byaccession.keys(), key=str.lower)

    @staticmethod
    def __get_family(entry):
        if not entry:
            return None

        family = Family()

        # Read the family attributes and data
        for k in entry.attrs:
            value = entry.attrs[k]
            setattr(family, k, value)

        return family

    def __get_family_raw_by_accession(self, accession):
        """Returns a handle to the data fo the family with the given accession."""
        return self.file["Families"].get(accession)

    def get_family_by_accession(self, accession):
        """Returns the family with the given accession."""
        entry = self.file["Families"].get(accession)
        return self.__get_family(entry)

    def get_family_by_name(self, name):
        """Returns the family with the given name."""
        entry = self.file["Families/ByName"].get(name)
        return self.__get_family(entry)


def walk_tree(tree):
    """Returns all elements in 'tree' with all levels flattened."""
    if hasattr(tree, "__iter__"):
        for elem in tree:
            yield from walk_tree(elem)
    else:
        yield tree


# Command-line utilities


def famdb_file_type(mode):
    """Returns a type suitable for use with argparse, opening a FamDB file when active."""
    return lambda filename: FamDB(filename, mode)


def command_names(args):
    """The 'names' command displays all names of all taxa that match the search term."""

    entries = []
    for tax_id in args.file.resolve_species(args.term):
        names = args.file.get_taxon_names(tax_id)
        entries += [[tax_id, names]]

    if args.format == "pretty":
        for (tax_id, names) in entries:
            print(tax_id, ", ".join(["{1} ({0})".format(*n) for n in names]))
    elif args.format == "json":
        obj = []
        for (tax_id, names) in entries:
            names_obj = [{"kind": name[0], "value": name[1]} for name in names]
            obj += [{"id": tax_id, "names": names_obj}]
        print(json.dumps(obj))
    else:
        raise ValueError("Unimplemented names format: %s" % args.format)


def print_lineage_tree(file, tree, gutter_self, gutter_children):
    """Pretty-prints a lineage tree with box drawing characters."""
    if not tree:
        return

    tax_id = tree[0]
    children = tree[1:]
    name = file.get_taxon_name(tax_id, 'scientific name')
    count = len(file.get_families_for_taxon(tax_id))
    print("{}{} {} [{}]".format(gutter_self, tax_id, name, count))

    if len(children) > 1:
        for child in children[:-1]:
            print_lineage_tree(file, child, gutter_children + "├─", gutter_children + "│ ")

    if children:
        print_lineage_tree(file, children[-1], gutter_children + "└─", gutter_children + "  ")


def print_lineage_semicolons(file, tree, parent_name):
    """Prints a lineage tree as a list of semicolon-delimited names."""
    if not tree:
        return

    tax_id = tree[0]
    children = tree[1:]
    name = file.get_taxon_name(tax_id, 'scientific name')
    if parent_name:
        name = parent_name + ";" + name

    count = len(file.get_families_for_taxon(tax_id))
    print("{}: {} [{}]".format(tax_id, name, count))

    for child in children:
        print_lineage_semicolons(file, child, name)

def command_lineage(args):
    """The 'lineage' command outputs ancestors and/or descendants of the given taxon."""

    target_id = args.file.resolve_one_species(args.term)
    tree = args.file.get_lineage(target_id, descendants=args.descendants, ancestors=args.ancestors)

    if args.format == "pretty":
        print_lineage_tree(args.file, tree, "", "")
    elif args.format == "semicolon":
        print_lineage_semicolons(args.file, tree, "")
    else:
        raise ValueError("Unimplemented lineage format: %s" % args.format)

def print_families(args, families, species=None):
    """Prints each family in 'families' in the requested format."""

    if len(families) > 1:
        db_info = args.file.get_db_info()
        if db_info:
            copyright_text = db_info["copyright"]
            # Add appropriate comment character to the copyright header lines
            if "hmm" in args.format:
                copyright_text = re.sub("(?m)^", "#   ", copyright_text)
            elif "fasta" in args.format:
                copyright_text = None
            elif "embl" in args.format:
                copyright_text = re.sub("(?m)^", "CC   ", copyright_text)
            if copyright_text:
                print(copyright_text)

    for family in families:
        if args.format == "summary":
            entry = str(family) + "\n"
        elif args.format == "hmm":
            entry = family.to_dfam_hmm(args.file)
        elif args.format == "hmm_species":
            entry = family.to_dfam_hmm(args.file, species)
        elif args.format == "fasta" or args.format == "fasta_name":
            entry = family.to_fasta(args.file)
        elif args.format == "fasta_acc":
            entry = family.to_fasta(args.file, use_accession=True)
        elif args.format == "embl":
            entry = family.to_embl(args.file)
        elif args.format == "embl_meta":
            entry = family.to_embl(args.file, include_meta=True, include_seq=False)
        elif args.format == "embl_seq":
            entry = family.to_embl(args.file, include_meta=False, include_seq=True)
        else:
            raise ValueError("Unimplemented family format: %s" % args.format)

        if entry:
            print(entry, end="")


def command_family(args):
    """The 'family' command outputs a single family by name or accession."""
    family = args.file.get_family_by_accession(args.term)
    if not family:
        family = args.file.get_family_by_name(args.term)

    if family:
        print_families(args, [family])
    else:
        print_families(args, [])


def command_families(args):
    """The 'families' command outputs all families associated with the given taxon."""
    target_id = args.file.resolve_one_species(args.term)

    families = []
    for accession in sorted(args.file.get_accessions_filtered(tax_id=target_id,
                                                              descendants=args.descendants,
                                                              ancestors=args.ancestors,
                                                              stage=args.stage,
                                                              repeat_type=args.repeat_type,
                                                              name=args.name)):
        family = args.file.get_family_by_accession(accession)

        families += [family]

    print_families(args, families, target_id)


def main():
    """Parses command-line arguments and runs the requested command."""

    logging.basicConfig()

    parser = argparse.ArgumentParser(description="Queries the contents of a famdb file.")
    parser.add_argument("-l", "--log-level", default="INFO")

    parser.add_argument("-i", "--file", type=famdb_file_type("r"), help="specifies the file to query")

    subparsers = parser.add_subparsers(help="Specifies the kind of query to perform. For more information, run e.g. famdb.py lineage --help")

    p_names = subparsers.add_parser("names", description="List the names and taxonomy identifiers of a clade.")
    p_names.add_argument("-f", "--format", default="pretty", choices=["pretty", "json"],
        help="choose output format. json is more appropriate for scripts.")
    p_names.add_argument("term", help="search term. Can be an NCBI taxonomy identifier or part of a scientific or common name")
    p_names.set_defaults(func=command_names)

    p_lineage = subparsers.add_parser("lineage", description="List the taxonomy tree including counts of families at each clade.")
    p_lineage.add_argument("-a", "--ancestors", action="store_true",
        help="include all ancestors of the given clade")
    p_lineage.add_argument("-d", "--descendants", action="store_true",
        help="include all descendants of the given clade")
    p_lineage.add_argument("-f", "--format", default="pretty", choices=["pretty", "semicolon"],
        help="choose output format. semicolon-delimited is more appropriate for scripts")
    p_lineage.add_argument("term", help="search term. Can be an NCBI taxonomy identifier or an unambiguous scientific or common name")
    p_lineage.set_defaults(func=command_lineage)

    family_formats = ["summary", "hmm", "hmm_species", "fasta_name", "fasta_acc", "embl", "embl_meta", "embl_seq"]

    p_families = subparsers.add_parser("families", description="Retrieve the families associated\
        with a given clade, optionally filtered by other additional criteria")
    p_families.add_argument("-a", "--ancestors", action="store_true",
        help="include all ancestors of the given clade")
    p_families.add_argument("-d", "--descendants", action="store_true",
        help="include all descendants of the given clade")
    p_families.add_argument("--stage", type=int,
        help="include only families that should be searched in the given stage")
    p_families.add_argument("--class", dest="repeat_type", type=str,
        help="include only families that have the specified repeat type")
    p_families.add_argument("--name", type=str,
        help="include only families whose name begins with this search term")
    p_families.add_argument("-f", "--format", default="summary", choices=family_formats,
        help="choose output format")
    p_families.add_argument("term", help="search term. Can be an NCBI taxonomy identifier or an unambiguous scientific or common name")
    p_families.set_defaults(func=command_families)

    p_family = subparsers.add_parser("family", description="Retrieve details of a single family.")
    p_family.add_argument("-f", "--format", default="summary", choices=family_formats,
        help="choose output format")
    p_family.add_argument("term", help="the accession of the family to be retrieved")
    p_family.set_defaults(func=command_family)

    args = parser.parse_args()
    logging.getLogger().setLevel(getattr(logging, args.log_level.upper()))
    if "func" in args:
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
