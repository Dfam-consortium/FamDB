# FamDB README for Developers

## Creating famdb files

`export_dfam.py` is used to build famdb files for Dfam releases. It
can be used in a few ways:

* Taxonomy can be sourced from the database, or from a local dump of the NCBI taxonomy.
* Families can be sourced from the database, from HMM, and/or from EMBL files.

Example: build a famdb file from a frozen Dfam release.

```
$ /usr/bin/time ./export_dfam.py --from-db mysql://user:pass@host/database --from-embl Supplemental.embl --count-taxa-in extra_taxa.txt Dfam_curatedonly.h5
$ /usr/bin/time ./export_dfam.py --from-db mysql://user:pass@host/database -r --from-embl Supplemental.embl --count-taxa-in extra_taxa.txt Dfam.h5
```

Example: build a famdb file from an HMM file

```
$ /usr/bin/time ./export_dfam.py --from-tax-dump /path/to/taxonomy --from-hmm=families.hmm --db-version=0.1 custom_hmms.h5
```

## Unit Tests

Unit tests are written with Python's `unittest` package, and the test modules
are named in a way that is discoverable by `unittest` automatically:

```
$ python3 -m unittest
```

Or by running the `check` target in the `Makefile`:

```
make check
```

The behavior of some tests can be controlled with these environment variables:

* `FAMDB_TEST_COVERAGE`: If non-empty, runs sub-tests inside an invocation of
  `coverage run`, so they can be included in coverage.
* `FAMDB_TEST_BLESS`: If non-empty, "blesses" the current actual output of CLI
  tests as the expected/desired output.

The `Makefile` also has a `coverage` target, which runs coverage in a way
that works with all unit tests and places output in the `htmlcov/` directory.

```
make coverage
```
