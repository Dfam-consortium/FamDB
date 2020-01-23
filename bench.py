#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
    Benchmark conversion and query times and file sizes for FamDB files.

    Usage: bench.py

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

import logging
import os
import random
import time

import famdb
import hmmfile
import taxonomy

LOGGER = logging.getLogger(__name__)


def run_time(func):
    """Runs func, returning the number of seconds taken to run and the return value of func."""
    start = time.perf_counter()
    value = func()
    end = time.perf_counter()
    return end - start, value


def run_import(infile, outfile, tax_db_src, extra_taxa_file_name, copies):
    """Runs import and measures time taken and resulting file size."""
    duration, tax_db = run_time(lambda: taxonomy.read_taxdb(tax_db_src))
    LOGGER.info("Read taxonomy in %f", duration)

    # Read in the "extra taxa" file and mark its entries as used taxa.
    with open(extra_taxa_file_name, "r") as extra_taxa_file:
        extra_taxa = extra_taxa_file.read(None)
    for entry in extra_taxa.split():
        tax_id = int(entry)
        tax_db[tax_id].mark_ancestry_used()

    def _do_import():
        nonlocal infile, outfile, tax_db_src, copies

        LOGGER.info("Importing families with %d copies each", copies)
        count = 0
        for family in hmmfile.iterate_hmm_file(infile):
            accession = family.accession
            name = family.name

            for copy in range(copies):
                family.accession = "BC{:02}{}".format(copy, accession)
                family.name = "BC{:02}{}".format(copy, name)
                count += 1

                # Associate the family to its relevant taxa and mark them as "used"
                for tax_id in family.extract_tax_ids():
                    tax_db[tax_id].families += [family.accession]
                    tax_db[tax_id].mark_ancestry_used()

                outfile.add_family(family)
                LOGGER.debug("Imported family %s (%s)", family.name, family.accession)

        LOGGER.info("Imported %d families", count)
        return count

    duration, count = run_time(_do_import)
    LOGGER.info("Wrote %d families in %f = %f families/sec", count, duration, count / duration)

    (duration, _) = run_time(lambda: outfile.write_taxonomy(tax_db))
    LOGGER.info("Wrote taxonomy in %f = %f families/sec", duration, count / duration)
    LOGGER.info("Finished import")

    stat = os.stat(outfile.file.filename)
    size = stat.st_size
    LOGGER.info("Total bytes %d = %d per family", size, size / count)


def run_queries(dbfile):
    """Runs queries and measures time taken."""
    def _do_random_queries():
        nonlocal dbfile, names, accessions

        for name in names:
            str(dbfile.get_family_by_name(name))

        for acc in accessions:
            str(dbfile.get_family_by_accession(acc))

        return len(names) + len(accessions)

    names = random.sample(dbfile.get_family_names(), 100)
    accessions = random.sample(dbfile.get_family_accessions(), 100)

    duration, count = run_time(_do_random_queries)
    LOGGER.info("Retrieved %d families in %f = %f families/sec", count, duration, count / duration)

    def _do_fetch_human():
        nonlocal dbfile

        accs = dbfile.get_accessions_filtered(tax_id=9606, ancestors=True)
        count = 0
        for acc in accs:
            count += 1
            str(dbfile.get_family_by_accession(acc))

        return count

    duration, count = run_time(_do_fetch_human)
    LOGGER.info("Retrieved human families (%d) in %f = %f families/sec",
                count, duration, count / duration)


def main():
    """Benchmarking entry point"""
    logging.basicConfig()
    logging.getLogger(None).setLevel(logging.INFO)

    in_name = "Dfam.hmm"
    tax_db_src = "ncbi_tax"
    extra_taxa_file_name = "taxonomy.list"
    copy_counts = [1, 5, 10]

    for copies in copy_counts:
        db_name = "bench/{}_BC{:02}.h5".format(in_name, copies)
        with open(in_name, "r") as infile:
            with famdb.FamDB(db_name, "w") as dbfile:
                LOGGER.info("Importing %s to %s with %d copies", in_name, db_name, copies)
                run_import(infile, dbfile, tax_db_src, extra_taxa_file_name, copies)

    for copies in copy_counts:
        out_name = "bench/{}_BC{:02}.h5".format(in_name, copies)
        with famdb.FamDB(out_name, "r") as dbfile:
            run_queries(dbfile)


if __name__ == "__main__":
    main()
