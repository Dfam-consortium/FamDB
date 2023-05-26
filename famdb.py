#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
    famdb.py, version 0.5
    Usage: famdb.py [-h] [-l LOG_LEVEL] [-i FILE] command ...

    Queries or modifies the contents of a famdb file. For more detailed help
    and information about program options, run `famdb.py --help` or
    `famdb.py <command> --help`.

    This program can also be used as a module. It provides classes and methods
    for working with FamDB files, which contain Transposable Element (TE)
    families and associated taxonomy data.

    # Classes
        Family: Metadata and model of a TE family.
        FamDB: HDF5-based format for storing Family objects.

SEE ALSO:
    Dfam: http://www.dfam.org

AUTHOR(S):
    Anthony Gray <anthony.gray@systemsbiology.org>
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
import json
import logging
import os
import re
import sys

from famdb_globals import LOGGER, FILE_DESCRIPTION, FAMILY_FORMATS_EPILOG
from famdb_helper_classes import Family
from famdb_helper_methods import sanitize_name
from famdb_classes import FamDB


# Command-line utilities
def command_info(args):
    """The 'info' command displays some of the stored metadata."""

    db_info = args.db_dir.get_db_info()
    counts = args.db_dir.get_counts()
    f_info = args.db_dir.get_metadata()

    print(
        f"""\
File: {os.path.realpath(args.db_dir.db_dir)}
FamDB Generator: {f_info["generator"]}
FamDB Format Version: {f_info["version"]}
FamDB Creation Date: {f_info["created"]}

Database: {db_info["name"]}
Version: {db_info["version"]}
Date: {db_info["date"]}

{db_info["description"]}

{counts['file']} Files Present
Total consensus sequences: {counts["consensus"]}
Total HMMs: {counts["hmm"]}
"""
    )
    args.db_dir.show_files()


def command_names(args):
    """The 'names' command displays all names of all taxa that match the search term."""

    entries = []
    entries += args.db_dir.resolve_names(args.term)

    if args.format == "pretty":
        prev_exact = None
        for (tax_id, partition, is_exact, names) in entries:
            if is_exact != prev_exact:
                if is_exact:
                    print("Exact Matches\n=============")
                else:
                    if prev_exact:
                        print()
                    print("Non-exact Matches\n=================")
                prev_exact = is_exact

            print(
                f"Taxon: {tax_id}, Partition: {partition}, Names: {', '.join([f'{n[1]} ({n[0]})' for n in names[:-1]])}"
            )

    elif args.format == "json":
        obj = []
        for (tax_id, partition, _, names) in entries:
            names_obj = [{"kind": name[0], "value": name[1]} for name in names]
            obj += [{"id": tax_id, "partition": partition, "names": names_obj}]
        print(json.dumps(obj))
    else:
        raise ValueError("Unimplemented names format: %s" % args.format)


def print_lineage_tree(file, tree, partition, gutter_self, gutter_children):
    """Pretty-prints a lineage tree with box drawing characters."""
    if not tree:
        return
    if type(tree) == str:
        tax_id = tree
        children = []
    else:
        tax_id = tree[0]
        children = tree[1:]

    if "_link:" in str(tax_id):
        tax_id = str(tax_id).split(":")[1]
    name, tax_partition = file.get_taxon_name(tax_id, "scientific name")
    fams = file.get_families_for_taxon(tax_id, tax_partition)
    count = (
        len(fams) if fams is not None else f"Partition {tax_partition} Not Installed"
    )
    print(f"{gutter_self}{tax_id} {name}({tax_partition}) [{count}]")

    # All but the last child need a downward-pointing line that will link up
    # to the next child, so this is split into two cases
    if len(children) > 1:
        for child in children[:-1]:
            print_lineage_tree(
                file,
                child,
                tax_partition,
                gutter_children + "├─",
                gutter_children + "│ ",
            )

    if children:
        print_lineage_tree(
            file,
            children[-1],
            tax_partition,
            gutter_children + "└─",
            gutter_children + "  ",
        )


def print_lineage_semicolons(file, tree, partition, parent_name, starting_at):
    """
    Prints a lineage tree as a flat list of semicolon-delimited names.

    In order to print the correct lineage string, the available tree must
    be "complete" even if ancestors were not specified to build up the
    string starting from "root". 'starting_at' specifies the first taxa
    (in the descending direction) to actually be output.
    """
    if not tree:
        return

    tax_id = tree[0]
    children = tree[1:]
    name, tax_partition = file.get_taxon_name(tax_id, "scientific name")
    if parent_name:
        name = parent_name + ";" + name

    if starting_at == tax_id:
        starting_at = None

    if not starting_at:
        count = len(file.get_families_for_taxon(tax_id, partition))
        print(f"{tax_id}({tax_partition}): {name} [{count}]")

    for child in children:
        print_lineage_semicolons(file, child, tax_partition, name, starting_at)


def get_lineage_totals(file, tree, target_id, partition, seen=None):
    """
    Recursively calculates the total number of families
    on ancestors and descendants of 'target_id' in the given 'tree'.

    'seen' is required to track families that are present on multiple
    lineages due to horizontal transfer and ensure each family
    is only counted one time, either as an ancestor or a descendant.
    """
    if not seen:
        seen = set()

    tax_id = tree[0]
    children = tree[1:]
    accessions = file.get_families_for_taxon(tax_id, partition)

    count_here = 0
    for acc in accessions:
        if acc not in seen:
            seen.add(acc)
            count_here += 1

    if target_id == tax_id:
        target_id = None

    counts = [0, 0]
    for child in children:
        anc, desc = get_lineage_totals(file, child, target_id, partition, seen)
        counts[0] += anc
        counts[1] += desc

    if target_id is None:
        counts[1] += count_here
    else:
        counts[0] += count_here

    return counts


def command_lineage(args):
    """The 'lineage' command outputs ancestors and/or descendants of the given taxon."""

    # TODO: like 'families', filter curated or uncurated (and other filters?)

    target_id, partition = args.db_dir.resolve_one_species(args.term)

    if not target_id:
        print(
            "No species found for search term '{}'".format(args.term), file=sys.stderr
        )
        return

    tree = args.db_dir.get_lineage_combined(
        target_id,
        descendants=args.descendants,
        ancestors=args.ancestors or args.format == "semicolon",
    )

    # TODO: prune branches with 0 total
    if args.format == "pretty":
        print_lineage_tree(args.db_dir, tree, partition, "", "")
    elif args.format == "semicolon":
        print_lineage_semicolons(args.db_dir, tree, partition, "", target_id)
    elif args.format == "totals":
        totals = get_lineage_totals(args.db_dir, tree, target_id, partition)
        print(
            "{} entries in ancestors; {} lineage-specific entries".format(
                totals[0], totals[1]
            )
        )
    else:
        raise ValueError("Unimplemented lineage format: %s" % args.format)


def print_families(args, families, header, species=None):
    """
    Prints each family in 'families', optionally with a copyright header. The
    format is determined by 'args.format' and additional data (such as
    taxonomy) is taken from 'args.db_dir'.

    If 'species' is provided and the format is "hmm_species", it is the id of
    the taxa whose species-specific thresholds should be substituted into the
    GA, NC, and TC lines of the HMM.
    """

    # These args are only available with the "families" command. When
    # print_families is called by the "family" command, accessing e.g.
    # args.stage directly raises an AttributeError
    # TODO: consider reworking argument passing to avoid this workaround
    add_reverse_complement = getattr(args, "add_reverse_complement", False)
    include_class_in_name = getattr(args, "include_class_in_name", False)
    require_general_threshold = getattr(args, "require_general_threshold", False)
    stage = getattr(args, "stage", None)

    if header:
        db_info = args.db_dir.get_db_info()
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
            entry = family.to_dfam_hmm(
                args.db_dir,
                include_class_in_name=include_class_in_name,
                require_general_threshold=require_general_threshold,
            )
        elif args.format == "hmm_species":
            entry = family.to_dfam_hmm(
                args.db_dir,
                species,
                include_class_in_name=include_class_in_name,
                require_general_threshold=require_general_threshold,
            )
        elif (
            args.format == "fasta"
            or args.format == "fasta_name"
            or args.format == "fasta_acc"
        ):
            use_accession = args.format == "fasta_acc"

            buffers = []
            if stage and family.buffer_stages:
                for spec in family.buffer_stages.split(","):
                    if "[" in spec:
                        matches = re.match(r"(\d+)\[(\d+)-(\d+)\]", spec.strip())
                        if matches:
                            if stage == int(matches.group(1)):
                                buffers += [
                                    [int(matches.group(2)), int(matches.group(3))]
                                ]
                        else:
                            LOGGER.warning(
                                "Ingored invalid buffer specification: '%s'",
                                spec.strip(),
                            )
                    else:
                        buffers += [stage == int(spec)]

            if not buffers:
                buffers += [None]

            entry = ""
            for buffer_spec in buffers:
                entry += (
                    family.to_fasta(
                        args.db_dir,
                        use_accession=use_accession,
                        include_class_in_name=include_class_in_name,
                        buffer=buffer_spec,
                    )
                    or ""
                )

                if add_reverse_complement:
                    entry += (
                        family.to_fasta(
                            args.db_dir,
                            use_accession=use_accession,
                            include_class_in_name=include_class_in_name,
                            do_reverse_complement=True,
                            buffer=buffer_spec,
                        )
                        or ""
                    )
        elif args.format == "embl":
            entry = family.to_embl(args.db_dir)
        elif args.format == "embl_meta":
            entry = family.to_embl(args.db_dir, include_meta=True, include_seq=False)
        elif args.format == "embl_seq":
            entry = family.to_embl(args.db_dir, include_meta=False, include_seq=True)
        else:
            raise ValueError("Unimplemented family format: %s" % args.format)

        if entry:
            print(entry, end="")


def command_family(args):
    """The 'family' command outputs a single family by name or accession."""
    family = args.db_dir.get_family_by_accession(args.accession)
    if not family:
        family = args.db_dir.get_family_by_name(args.accession)

    if family:
        print_families(args, [family], False)


def command_families(args):
    """The 'families' command outputs all families associated with the given taxon."""
    target_id = args.db_dir.resolve_one_species(args.term)

    if not target_id:
        print(f"No species found for search term '{args.term}'", file=sys.stderr)
        return

    families = []

    is_hmm = args.format.startswith("hmm")

    # NB: This is speed-inefficient, because get_accessions_filtered needs to
    # read the whole family data even though we read it again right after.
    # However it is *much* more memory-efficient than loading all the family
    # data at once and then sorting by accession.
    accessions = sorted(
        args.db_dir.get_accessions_filtered(
            tax_id=target_id,
            descendants=args.descendants,
            ancestors=args.ancestors,
            curated_only=args.curated,
            uncurated_only=args.uncurated,
            is_hmm=is_hmm,
            stage=args.stage,
            repeat_type=args.repeat_type,
            name=args.name,
        )
    )

    families = map(args.db_dir.get_family_by_accession, accessions)

    print_families(args, families, True, target_id)


def command_append(args):
    """
    The 'append' command reads an EMBL file and appends its entries to an
    existing famdb file.
    """

    lookup = {}
    for tax_id, names in args.db_dir.names_dump.items():
        for name in names:
            if name[0] == "scientific name":
                sanitized_name = sanitize_name(name[1]).lower()
                lookup[sanitized_name] = int(tax_id)

    header = None

    def set_header(val):
        nonlocal header
        header = val

    embl_iter = Family.read_embl_families(args.infile, lookup, set_header)

    seen_accs = args.db_dir.seen["accession"]
    seen_names = args.db_dir.seen["name"]

    for entry in embl_iter:
        acc = entry.accession
        # TODO: This is awkward. The EMBL files being appended may only have an
        # "accession", but that accession may match the *name* of a family
        # already in Dfam. The accession may also match a family already in
        # Dfam, but with a "v" added.
        if (
            acc in seen_accs
            or acc in seen_names
            or acc + "v" in seen_accs
            or acc + "v" in seen_names
        ):
            LOGGER.debug("Ignoring duplicate entry %s", entry.accession)
        else:
            args.db_dir.add_family(entry)

    db_info = args.db_dir.get_db_info()

    if args.name:
        db_info["name"] = args.name
    if args.description:
        db_info["description"] += "\n" + args.description

    db_info["copyright"] += f"\n\n{header}"

    args.db_dir.set_db_info(
        db_info["name"],
        db_info["version"],
        db_info["date"],
        db_info["description"],
        db_info["copyright"],
    )

    # Write the updated counts and metadata
    args.db_dir.finalize()


def main():  # ================================================================================================================================
    """Parses command-line arguments and runs the requested command."""

    logging.basicConfig()

    parser = argparse.ArgumentParser(
        description=FILE_DESCRIPTION,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("-l", "--log-level", default="INFO")

    parser.add_argument("-i", "--db_dir", help="specifies the file to query")

    subparsers = parser.add_subparsers(
        description="""Specifies the kind of query to perform.
For more information on all the possible options for a command, add the --help option after it:
famdb.py families --help
"""
    )
    # INFO --------------------------------------------------------------------------------------------------------------------------------
    p_info = subparsers.add_parser(
        "info", description="List general information about the file."
    )
    p_info.set_defaults(func=command_info)

    # NAMES --------------------------------------------------------------------------------------------------------------------------------
    p_names = subparsers.add_parser(
        "names", description="List the names and taxonomy identifiers of a clade."
    )
    p_names.add_argument(
        "-f",
        "--format",
        default="pretty",
        choices=["pretty", "json"],
        metavar="<format>",
        help="choose output format. The default is 'pretty'. 'json' is more appropriate for scripts.",
    )
    p_names.add_argument(
        "term",
        nargs="+",
        help="search term. Can be an NCBI taxonomy identifier or part of a scientific or common name",
    )
    p_names.set_defaults(func=command_names)

    # LINEAGE --------------------------------------------------------------------------------------------------------------------------------
    p_lineage = subparsers.add_parser(
        "lineage",
        description="List the taxonomy tree including counts of families at each clade.",
    )
    p_lineage.add_argument(
        "-a",
        "--ancestors",
        action="store_true",
        help="include all ancestors of the given clade",
    )
    p_lineage.add_argument(
        "-d",
        "--descendants",
        action="store_true",
        help="include all descendants of the given clade",
    )
    p_lineage.add_argument(
        "-f",
        "--format",
        default="pretty",
        choices=["pretty", "semicolon", "totals"],
        metavar="<format>",
        help="choose output format. The default is 'pretty'. 'semicolon' is more appropriate for scripts. 'totals' displays the number of ancestral and lineage-specific families found.",
    )
    p_lineage.add_argument(
        "term",
        nargs="+",
        help="search term. Can be an NCBI taxonomy identifier or an unambiguous scientific or common name",
    )
    p_lineage.set_defaults(func=command_lineage)

    # FAMILIES --------------------------------------------------------------------------------------------------------------------------------
    family_formats = [
        "summary",
        "hmm",
        "hmm_species",
        "fasta_name",
        "fasta_acc",
        "embl",
        "embl_meta",
        "embl_seq",
    ]
    family_formats_epilog = FAMILY_FORMATS_EPILOG

    p_families = subparsers.add_parser(
        "families",
        description="Retrieve the families associated \
with a given clade, optionally filtered by additional criteria",
        epilog=family_formats_epilog,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p_families.add_argument(
        "-a",
        "--ancestors",
        action="store_true",
        help="include all ancestors of the given clade",
    )
    p_families.add_argument(
        "-d",
        "--descendants",
        action="store_true",
        help="include all descendants of the given clade",
    )
    p_families.add_argument(
        "--stage",
        type=int,
        help="include only families that should be searched in the given stage",
    )
    p_families.add_argument(
        "--class",
        dest="repeat_type",
        type=str,
        help="include only families that have the specified repeat Type/SubType",
    )
    p_families.add_argument(
        "--name",
        type=str,
        help="include only families whose name begins with this search term",
    )
    p_families.add_argument(
        "--uncurated",
        action="store_true",
        help="include only 'uncurated' families (i.e. named DRXXXXXXX)",
    )
    p_families.add_argument(
        "--curated",
        action="store_true",
        help="include only 'curated' families (i.e. not named DRXXXXXXX)",
    )
    p_families.add_argument(
        "-f",
        "--format",
        default="summary",
        choices=family_formats,
        metavar="<format>",
        help="choose output format.",
    )
    p_families.add_argument(
        "--add-reverse-complement",
        action="store_true",
        help="include a reverse-complemented copy of each matching family; only suppported for fasta formats",
    )
    p_families.add_argument(
        "--include-class-in-name",
        action="store_true",
        help="include the RepeatMasker type/subtype after the name (e.g. HERV16#LTR/ERVL); only supported for hmm and fasta formats",
    )
    p_families.add_argument(
        "--require-general-threshold",
        action="store_true",
        help="skip families missing general thresholds (and log their accessions at the debug log level)",
    )
    p_families.add_argument(
        "term",
        nargs="+",
        help="search term. Can be an NCBI taxonomy identifier or an unambiguous scientific or common name",
    )
    p_families.set_defaults(func=command_families)

    # FAMILY --------------------------------------------------------------------------------------------------------------------------------
    p_family = subparsers.add_parser(
        "family",
        description="Retrieve details of a single family.",
        epilog=family_formats_epilog,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p_family.add_argument(
        "-f",
        "--format",
        default="summary",
        choices=family_formats,
        metavar="<format>",
        help="choose output format.",
    )
    p_family.add_argument(
        "accession", help="the accession of the family to be retrieved"
    )
    p_family.set_defaults(func=command_family)

    # APPEND --------------------------------------------------------------------------------------------------------------------------------
    p_append = subparsers.add_parser("append")
    p_append.add_argument("infile", help="the name of the input file to be appended")
    p_append.add_argument(
        "--name", help="new name for the database (replaces the existing name)"
    )
    p_append.add_argument(
        "--description",
        help="additional database description (added to the existing description)",
    )
    p_append.set_defaults(func=command_append)

    args = parser.parse_args()
    logging.getLogger().setLevel(getattr(logging, args.log_level.upper()))

    if "term" in args:
        args.term = " ".join(args.term)

    # For RepeatMasker: Try Libraries/RepeatMaskerLib.h5, if no file was specified
    # in the arguments and that file exists.
    if not args.db_dir:
        # sys.path[0], if non-empty, is initially set to the directory of the
        # originally-invoked script.
        if sys.path[0]:
            default_db_dir = os.path.join(
                sys.path[0], "./dfam"
            )  # TODO: update file name
            if os.path.exists(default_db_dir):
                args.db_dir = default_db_dir

    if args.db_dir and os.path.isdir(args.db_dir):
        try:
            if "func" in args and args.func is command_append:
                mode = "r+"
            else:
                mode = "r"

            args.db_dir = FamDB(args.db_dir, mode)
        except:
            args.db_dir = None

            exc_value = sys.exc_info()[1]
            LOGGER.error("Error reading file: %s", exc_value)
            if LOGGER.getEffectiveLevel() <= logging.DEBUG:
                raise
    else:
        LOGGER.error(
            "Please specify a directory to operate on with the -i/--db_dir option."
        )
        return

    if "func" in args:
        args.func(args)
    else:
        parser.print_help()
        args.db_dir.show_files()


if __name__ == "__main__":
    try:
        main()
    except BrokenPipeError:
        # This workaround is from
        # https://docs.python.org/3/library/signal.html#note-on-sigpipe

        # Python flushes standard streams on exit; redirect remaining output
        # to devnull to avoid another BrokenPipeError at shutdown
        devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull, sys.stdout.fileno())
        sys.exit(1)  # Python exits with error code 1 on EPIPE
