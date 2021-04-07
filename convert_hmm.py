#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
    Convert Dfam-style hmm files to and from FamDB.

    Usage: hmm_convert.py [-h] [-l LOG_LEVEL] command ...

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

import argparse
import datetime
import logging

import famdb
import hmmfile
import taxonomy

LOGGER = logging.getLogger(__name__)


def famdb_file_type(mode):
    """Returns a type suitable for use with argparse, opening a FamDB file when active."""
    return lambda filename: famdb.FamDB(filename, mode)


def command_import(args):
    """The 'import' command converts a Dfam-style hmm file to a FamDB file."""
    tax_db = taxonomy.read_taxdb(args.tax_db)

    # Read in the "extra taxa" file and mark its entries as used taxa
    if args.extra_taxa_file:
        with open(args.extra_taxa_file, "r") as extra_taxa_file:
            contents = extra_taxa_file.read(None)
        for entry in contents.split():
            tax_id = int(entry)
            tax_db[tax_id].mark_ancestry_used()

    version = args.db_version
    date = args.db_date or datetime.date.today().strftime("%Y-%m-%d")
    description = "TODO: convert_hmm.py description not yet implemented"
    copyright_text = "TODO: convert_hmm.py copyright not yet implemented"

    args.outfile.set_db_info("Dfam", version, date, description, copyright_text)

    taxid_lookup = {}
    for (tax_id, node) in tax_db.items():
        for [name_class, name_txt] in node.names:
            if name_class == "scientific name":
                sanitized_name = famdb.sanitize_name(name_txt).lower()
                taxid_lookup[sanitized_name] = int(tax_id)

    LOGGER.info("Importing families")
    count = 0
    for family in hmmfile.iterate_hmm_file(args.infile, tax_db, taxid_lookup):
        count += 1

        # Associate the family to its relevant taxa and mark them as "used"
        for tax_id in family.clades:
            tax_db[tax_id].families += [family.accession]
            tax_db[tax_id].mark_ancestry_used()

        args.outfile.add_family(family)
        LOGGER.debug("Imported family %s (%s)", family.name, family.accession)
    LOGGER.info("Imported %d families", count)

    args.outfile.write_taxonomy(tax_db)

    LOGGER.info("Finished import")


def command_dump(args):
    """The 'dump' command exports the contents of a FamDB file to Dfam-style hmm format."""
    count = 0
    for name in args.infile.get_family_names():
        count += 1
        family = args.infile.get_family_by_name(name)

        # Write the family to the hmm file and append a separator
        args.outfile.write(family.model)

        LOGGER.debug("Exported family %s (%s)", family.name, family.accession)
    LOGGER.info("Exported %d families", count)

    LOGGER.info("Finished export")


def main():
    """Parses command-line arguments and runs the requested command."""

    logging.basicConfig()

    parser = argparse.ArgumentParser()
    parser.add_argument("-l", "--log-level", default="INFO")
    subparsers = parser.add_subparsers(title="modes")

    p_import = subparsers.add_parser("import")
    p_import.add_argument("-t", "--tax-db", required=True)
    p_import.add_argument("-e", "--extra-taxa-file", help="One taxonomy ID per line (NB: does not match export_dfam.py)")
    p_import.add_argument("--db-version", required=True, help="database version")
    p_import.add_argument("--db-date", help="database date, in YYYY-MM-DD format (default today)")
    p_import.add_argument("infile", type=argparse.FileType("r"))
    p_import.add_argument("outfile", type=famdb_file_type("w"))
    p_import.set_defaults(func=command_import)

    p_dump = subparsers.add_parser("dump")
    p_dump.add_argument("infile", type=famdb_file_type("r"))
    p_dump.add_argument("outfile", type=argparse.FileType("w"))
    p_dump.set_defaults(func=command_dump)

    args = parser.parse_args()
    logging.getLogger().setLevel(getattr(logging, args.log_level.upper()))
    if "func" in args:
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
