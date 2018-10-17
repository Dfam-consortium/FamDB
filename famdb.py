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
import logging

import h5py
import numpy


LOGGER = logging.getLogger(__name__)


class Family:
    """A Transposable Element family, made up of metadata and a model."""

    FamilyField = collections.namedtuple("FamilyField", ["name", "type"])

    # Known metadata fields
    META_FIELDS = [
        # Core required family metadata
        FamilyField("name", str),
        FamilyField("accession", str),
        FamilyField("consensus", str),
        FamilyField("length", int),

        # Optional family metadata
        FamilyField("description", str),
        FamilyField("author", str),
        FamilyField("classification", list),
        FamilyField("classification_note", str),
        FamilyField("search_stages", str),
        FamilyField("buffer_stages", str),
        FamilyField("clades", list),
        FamilyField("date_created", str),
        FamilyField("date_modified", str),
        FamilyField("thresholds", list),
        FamilyField("type", str),
        FamilyField("subtype", str),
        FamilyField("features", str),
        FamilyField("aliases", list),
        FamilyField("citations", list),
        FamilyField("refineable", bool),
        FamilyField("target_site_cons", str),
    ]

    # Metadata lookup by field name
    META_LOOKUP = {field.name: field for field in META_FIELDS}

    def __init__(self):
        super().__setattr__("meta", {})
        self.model = ""

    @staticmethod
    def type_for(name):
        """Returns the expected data type for the attribute 'name'."""
        return Family.META_LOOKUP[name].type

    def __getattr__(self, name):
        if name not in Family.META_LOOKUP:
            raise AttributeError("Unknown Family metadata attribute '{}'".format(name))

        value = self.meta.get(name)

        # Initialize empty values
        if not value:
            data_ty = self.type_for(name)
            if data_ty is list:
                self.meta[name] = value = []

        return value

    def __setattr__(self, name, value):
        if name in Family.META_LOOKUP:
            expected_type = self.type_for(name)
            if not isinstance(value, expected_type):
                try:
                    value = expected_type(value)
                except:
                    raise TypeError("Incompatible type for '{}'. Expected '{}', got '{}'".format(
                        name, expected_type, type(value)))
            self.meta[name] = value
        elif name in ["model"]:
            super().__setattr__(name, value)
        else:
            raise AttributeError("Unknown Family metadata attribute '{}'".format(name))

    def extract_tax_ids(self):
        """
        Return the taxonomy IDs associated with this Family,
        extracted from the 'clades' metadata field.
        """
        return map(int, self.clades)


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
        self.__check_unique(family, "name")
        self.__check_unique(family, "accession")

        # Create the family data
        dset = self.group_families.create_dataset(family.accession,
                                                  data=family.model,
                                                  dtype=FamDB.dtype_str)

        # Set the family attributes
        for k in Family.META_LOOKUP:
            value = getattr(family, k)
            if value:
                if isinstance(value, list):
                    value = "\n".join(value)
                dset.attrs[k] = value

        # Create links
        self.group_byname[family.name] = h5py.SoftLink("/Families/" + family.accession)
        self.group_byaccession[family.accession] = h5py.SoftLink("/Families/" + family.accession)

        LOGGER.debug("Added family %s (%s)", family.name, family.accession)

    def write_taxonomy(self, tax_db):
        """Writes taxonomy nodes in 'tax_db' to the database."""
        LOGGER.info("Writing taxonomy nodes to database")

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

        LOGGER.info("Wrote %d taxonomy nodes", count)

    def has_taxon(self, tax_id):
        """Returns True if 'self' has a taxonomy entry for 'tax_id'"""
        return str(tax_id) in self.group_nodes

    def search_taxon_names(self, text, kind=None):
        """
        Searches 'self' for taxons with a name containing 'text' and yields the
        ids of matching nodes. A list of strings may be passed as 'kind' to
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

    def resolve_species(self, term, kind=None):
        """
        Resolves 'term' as a species or clade in 'self'. If 'term' is a number,
        it is a taxon id. Otherwise, it will be searched for in 'self' in the
        name fields of all taxa. A list of strings may be passed as 'kind' to
        restrict what kinds of names will be searched.

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
        return self.search_taxon_names(term, kind)

    def resolve_one_species(self, term, kind=None):
        """
        Resolves 'term' in 'dbfile' as a taxon id or search term unambiguously.
        Parameters are as in the 'resolve_species' method.
        Raises an exception if not exactly one result is found.
        """

        results = list(self.resolve_species(term, kind))
        if len(results) == 1:
            return results[0]

        raise Exception("Ambiguous search term '{}' (found {} results)".format(term, len(results)))

    def get_taxon_names(self, tax_id, kind=None):
        """
        Returns a list of [name_class, name_value] of the taxon given by 'tax_id'.
        If kind is not 'None' (the default), only names of the given kind will be returned.
        """

        names = self.group_nodes[str(tax_id)]["Names"]
        if kind:
            return [name[1] for name in names if name[0] == kind]
        return names[:, :]

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

    def get_families_for_lineage(self, tax_id, **kwargs):
        """
        Yields accessions for the families requested. 'tax_id' and 'kwargs'
        correspond to the same arguments for 'get_lineage'.
        """

        for node in walk_tree(self.get_lineage(tax_id, **kwargs)):
            yield from self.get_families_for_taxon(node)

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
            if Family.type_for(k) is list:
                value = value.split("\n")
            setattr(family, k, value)

        family.model = entry[()]

        return family

    def get_family_by_accession(self, accession):
        """Returns the family with the given accession."""
        entry = self.file["Families"].get(accession)
        return self.__get_family(entry)

    def get_family_by_name(self, name):
        """Returns the family with the given name."""
        entry = self.file["Families/ByName"].get(name)
        return self.__get_family(entry)


def walk_tree(tree):
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

    if args.batch:
        # TODO: batch mode output format
        raise NotImplementedError()
    else:
        for (tax_id, names) in entries:
            print(tax_id, ", ".join(["{1} ({0})".format(*n) for n in names]))


def print_lineage_tree(file, tree, gutter_self, gutter_children):
    """Pretty-prints a lineage tree with box drawing characters."""
    if not tree:
        return

    tax_id = tree[0]
    children = tree[1:]
    name = file.get_taxon_names(tax_id, 'scientific name')[0]
    count = len(file.get_families_for_taxon(tax_id))
    print("{}{} {} [{}]".format(gutter_self, tax_id, name, count))

    if len(children) > 1:
        for child in children[:-1]:
            print_lineage_tree(file, child, gutter_children + "├─", gutter_children + "│ ")

    if children:
        print_lineage_tree(file, children[-1], gutter_children + "└─", gutter_children + "  ")


def command_lineage(args):
    """The 'lineage' command outputs ancestors and/or descendants of the given taxon."""

    target_id = args.file.resolve_one_species(args.term)
    tree = args.file.get_lineage(target_id, descendants=args.descendants, ancestors=args.ancestors)

    if args.batch:
        # TODO: batch mode output format
        raise NotImplementedError()
    else:
        print_lineage_tree(args.file, tree, "", "")


def command_family(args):
    """The 'family' command outputs a single family by name or accession."""
    family = args.file.get_family_by_accession(args.term)
    if not family:
        family = args.file.get_family_by_name(args.term)

    if args.batch:
        # TODO: batch mode output format
        print(family)
    else:
        print(family)


def command_families(args):
    """The 'families' command outputs all families associated with the given taxon."""
    target_id = args.file.resolve_one_species(args.term)

    families = []
    for accession in args.file.get_families_for_lineage(target_id,
                                                        descendants=args.descendants,
                                                        ancestors=args.ancestors):
        families += [args.file.get_family_by_accession(accession)]

    if args.batch:
        # TODO: batch mode output format
        for family in families:
            print(family)
    else:
        for family in families:
            print(family)


def main():
    """Parses command-line arguments and runs the requested command."""

    logging.basicConfig()

    parser = argparse.ArgumentParser()
    parser.add_argument("-l", "--log-level", default="INFO")
    subparsers = parser.add_subparsers(title="modes")

    p_query = subparsers.add_parser("query")
    p_query.add_argument("-b", "--batch", action="store_true")
    p_query.add_argument("file", type=famdb_file_type("r"))
    p_query_sub = p_query.add_subparsers()

    p_names = p_query_sub.add_parser("names")
    p_names.add_argument("term")
    p_names.set_defaults(func=command_names)

    p_lineage = p_query_sub.add_parser("lineage")
    p_lineage.add_argument("-a", "--ancestors", action="store_true")
    p_lineage.add_argument("-d", "--descendants", action="store_true")
    p_lineage.add_argument("term")
    p_lineage.set_defaults(func=command_lineage)

    p_families = p_query_sub.add_parser("families")
    p_families.add_argument("-a", "--ancestors", action="store_true")
    p_families.add_argument("-d", "--descendants", action="store_true")
    p_families.add_argument("term")
    p_families.set_defaults(func=command_families)

    p_family = p_query_sub.add_parser("family")
    p_family.add_argument("term")
    p_family.set_defaults(func=command_family)

    args = parser.parse_args()
    logging.getLogger().setLevel(getattr(logging, args.log_level.upper()))
    if "func" in args:
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
