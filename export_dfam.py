#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
    Export the dfam database to FamDB format.

    Usage: export_dfam.py [-h] [-l LOG_LEVEL]
               [--db-partition]
               [--from-db mysql://...] [-r]
               [--from-tax-dump ncbi_tax/]
               [--from-embl file.embl [--from-embl file2.embl ...]]
               [--from-hmm file.hmm [--from-hmm file2.hmm ...]]
               [--db-version 3.2]
               [--db-date YYYY-MM-DD]
               [--count-taxa-in taxa.txt]
               outfile


    WARNING: For DB exports this uses 47GB of RAM (as of Dfam 3.7) to hold
             auxiliary tables during export.  Do not run this on the production
             server or on an NFS partition.

    Data source options:

    --db-partition           : Path to definition file (F) produced by DfamPartition.py. Outputs one file per partition
    -p, --partition          : Specify which partitions in F to export. Defaults to all partitions.
    --from-db                : Connection string to MySQL database to import from
    -r, --include-uncurated  : Include uncurated families (DR*) records, not only DF* (the default)
    --from-tax-dump          : Use taxonomy from NCBI database dump, instead of the database
                               (or if building from files instead of the database)
    --from-embl              : Additional Dfam EMBL-formatted file to import; can be given multiple times.
    --from-hmm               : Additional Dfam HMM-formatted file to import; can be given multiple times.

    --count-taxa-in : Counts taxa from a file (one line per "family") for the purpose of building and
                      filtering the taxonomy tree. The resulting file will include the taxonomy data
                      for each node with any families assigned and for each that occurs in a
                      count-taxa-in file.  Nodes with more families assigned to them in either way
                      also have more of their children included in the tree.

                      E.g:
                      fgrep Species RMRBMeta.embl |
                         perl -ne '{ if ( /Species:\s+(\S.*)/ ) { print "$1\n"; }}' > repbase_list.txt

    Metadata options:

    --db-version    : Set the database version explicitly, overriding the version in --from-db if present.
    --db-date       : Set the database date explicitly, overriding the date in --from-db if present.
                      If not given, the current date will be used.

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
import itertools
import json
import logging
import re
import time
import sqlalchemy

import dfam_35 as dfam
from famdb_classes import FamDB, FamDBRoot
from famdb_data_loaders import (
    load_taxonomy_from_db,
    load_taxonomy_from_dump,
    iterate_db_families,
    read_hmm_families,
)
from famdb_globals import LOGGER, DESCRIPTION, COPYRIGHT_TEXT
from famdb_helper_classes import Family


def build_file_map(F, out_str, tax_db):
    file_map = {
        int(f): {
            "T_root": F[f]["T_root"],
            "filename": f"{out_str}.{f}.h5",
            "F_roots": F[f]["F_roots"],
        }
        for f in F
    }
    for file in file_map:
        file_map[file]["T_root_name"] = [
            name[1]
            for name in tax_db[file_map[file]["T_root"]].names
            if name[0] == "scientific name"
        ][0]
        F_roots_names = []
        F_roots = file_map[file]["F_roots"]
        if len(F_roots) > 1:
            for root in F_roots:
                F_roots_names += [
                    name[1]
                    for name in tax_db[root].names
                    if name[0] == "scientific name"
                ]
        file_map[file]["F_roots_names"] = F_roots_names
    return file_map


def export_families(
    args, session, tax_db, tax_lookup, partition
):  # pylint: disable=too-many-locals,too-many-branches,too-many-statements
    """Exports from a Dfam database to a FamDB file."""

    to_import = []
    target_count = 0

    if args.from_db:
        limit = 5 if args.test_set else None
        # SELECT * FROM `family` JOIN `family_clade` ON family_id=id WHERE dfam_taxdb_tax_id IN (taxa)
        query = (
            session.query(dfam.Family)
            .join(
                dfam.t_family_clade,
                dfam.Family.id == dfam.t_family_clade.c.family_id,
            )
            .filter(dfam.t_family_clade.c.dfam_taxdb_tax_id.in_(partition["nodes"]))
        ).limit(limit)

        # TODO: assuming that partitioned chunk files will include uncurated data
        if not args.include_uncurated and not args.db_partition:
            query = query.filter(dfam.Family.accession.like("DF%"))

        # TODO: This filter should be re-enabled later
        # .filter(dfam.Family.disabled != 1)

        target_count += query.count()
        LOGGER.info("Including %d families from database", target_count)

        to_import = itertools.chain(
            to_import, iterate_db_families(session, tax_db, query)
        )

    for embl_file in args.from_embl:
        LOGGER.info("Including all families from file: %s", embl_file)
        to_import = itertools.chain(
            to_import, Family.read_embl_families(embl_file, tax_lookup)
        )

    for hmm_file in args.from_hmm:
        LOGGER.info("Including all families from file: %s", hmm_file)
        to_import = itertools.chain(
            to_import, read_hmm_families(hmm_file, tax_db, tax_lookup)
        )

    if args.from_embl or args.from_hmm:
        LOGGER.info(
            "File sources are not counted in advance; only progress for db families will be reported."
        )

    start = time.perf_counter()
    report_start = start
    # Note about timing.  At this stage we haven't executed the iterate_db_families function yet
    # to iterate over the yielded family objects.  Therefore, the first time through this loop there
    # will be some overhead while it loads the classification nodes.  The remaining cycles will only
    # include the inner yeild loop in iterate_db_families.
    report_every = 1000
    if target_count > 1000000:
        report_every = int(target_count / 10000)

    count = 0
    for family in to_import:
        count += 1
        for clade_id in family.clades:
            # Associate the family to its relevant taxa
            tax_db[clade_id].families += [family.accession]

        args.outfile.add_family(family)
        LOGGER.debug("Imported family %s (%s)", family.name, family.accession)

        if (count % report_every) == 0:
            current = time.perf_counter()
            total_elapsed = current - start
            report_elapsed = current - report_start
            avg_time_per = total_elapsed / count
            curr_time_per = report_elapsed / report_every
            LOGGER.info(
                "%5d / %5d : %.3f avg secs per family : %.3f curr secs per family : %s HH:MM:SS remaining"
                % (
                    count,
                    target_count,
                    avg_time_per,
                    curr_time_per,
                    str(
                        datetime.timedelta(
                            seconds=(curr_time_per * (target_count - count))
                        )
                    ),
                )
            )
            report_start = time.perf_counter()

    delta = time.perf_counter() - start
    LOGGER.info(
        "Imported %d families in %s", count, str(datetime.timedelta(seconds=delta))
    )


def main():
    """Parses command-line arguments and runs the import."""

    logging.basicConfig()

    parser = argparse.ArgumentParser()
    parser.add_argument("-l", "--log-level", default="INFO")
    parser.add_argument("--from-db")
    parser.add_argument("--db-partition", required=True)
    parser.add_argument("-p", "--partition", nargs="+", default=[])
    parser.add_argument("-t", "--test_set", default=False)
    parser.add_argument("--from-tax-dump")
    parser.add_argument("-r", "--include-uncurated", action="store_true")
    parser.add_argument("--from-embl", action="append", default=[])
    parser.add_argument("--from-hmm", action="append", default=[])
    parser.add_argument("--db-version")
    parser.add_argument("--db-date")
    parser.add_argument("--count-taxa-in")
    parser.add_argument("outfile")  # , type=famdb_file_type("w"))

    args = parser.parse_args()
    logging.getLogger().setLevel(getattr(logging, args.log_level.upper()))

    # establish session, tax_db and tax_lookup to prevent restablishing for each chunk
    engine = sqlalchemy.create_engine(args.from_db)
    session = sqlalchemy.orm.Session(bind=engine)

    db_version = None
    db_date = None
    if args.from_db:
        version_info = session.query(dfam.DbVersion).one()
        db_version = version_info.dfam_version
        db_date = version_info.dfam_release_date.strftime("%Y-%m-%d")

    # Command-line overrides from db_version, db_date
    if args.db_version:
        db_version = args.db_version
    if args.db_date:
        db_date = args.db_date

    if not db_version:
        raise Exception(
            "Could not determine database version. Please use --from-db or --db-version."
        )
    if not db_date:
        db_date = datetime.date.today().strftime("%Y-%m-%d")

    year_match = re.match(r"(\d{4})-", db_date)
    if year_match:
        db_year = year_match.group(1)
    else:
        raise Exception("Date should be in YYYY-MM-DD format, got: " + db_date)

    copyright_text = COPYRIGHT_TEXT % (
        db_year,
        db_version,
        db_date,
    )

    out_str = args.outfile

    # load F early to verify metadata
    with open(args.db_partition, "r") as F_file:
        F_file = json.load(F_file)
    F = F_file["F"]
    F_meta = F_file["meta"]
    if F_meta["db_version"] != db_version or F_meta["db_date"] != db_date:
        LOGGER.error(
            "The partition information does not match the current database. Re-partition before export."
        )
        exit()

    # load taxonomy data
    if not args.from_tax_dump:
        tax_db, tax_lookup = load_taxonomy_from_db(session)
    else:
        tax_db, tax_lookup = load_taxonomy_from_dump(args.from_tax_dump)

    file_map = build_file_map(F, out_str, tax_db)
    file_info = {"meta": F_meta, "file_map": file_map}

    if args.partition:
        LOGGER.info(f"Exporting Partitions {args.partition}")
    else:
        args.partition = F.keys()
        LOGGER.info("Exporting All Partitions")

    for n in F:
        if n in args.partition:
            LOGGER.info(f"\tExporting chunk {n}")
            if n == "0":
                args.outfile = FamDBRoot(f"{out_str}.{n}.h5", "w")
                args.outfile.write_taxa_names(tax_db, {n: F[n]["nodes"] for n in F})
            else:
                args.outfile = FamDB(f"{out_str}.{n}.h5", "w")
            args.outfile.set_partition_info(n)
            args.outfile.set_file_info(file_info)
            args.outfile.set_db_info(
                "Dfam", db_version, db_date, DESCRIPTION, copyright_text
            )
            nodes = F[n]["nodes"]
            export_families(args, session, tax_db, tax_lookup, partition=F[n])
            args.outfile.write_taxonomy(tax_db, nodes)
            args.outfile.finalize()

    LOGGER.info("Finished import")


if __name__ == "__main__":
    main()
