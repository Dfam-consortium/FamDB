# FamDB README for Developers

## Software Structure

### FamDBLeaf
The basic file for storing Dfam data. Provides methods for writing and retrieving data to `.h5` files.

Data Groups:
* Families - Contains the TE family data elements
* Lookup - Contains subdirectories `ByName` and `ByStage` with links to the relevant family elements
* Taxonomy - Contains taxonomy structure data, as well as links to related family elements

### FamDBRoot
An extension (subclass) of FamDBLeaf that contains additional taxonomy and partition information.

Data Groups:
* Contains all FamDBLeaf data fields and functions.
* Partitions - Contains a subgroup for each partition. Each subgroup contains a mapping of taxonomy ids within that partition to their scientific and common names

### FamDB
A class for accessing unified data across a FamDBRoot file and any number of FamDBLeaf files. It verifies that all files in a directory are able to be used together (from the same partition, the same export, contains exactly 1 root file, ect.) and provides functions that collect and collate requested data from multiple files. 

### `famdb.py`
The python script invoked by the user. Mediates between the user provided arguments and the functions on an instance of FamDB.


## Creating famdb files

Before exporting to FamDB be sure that there is a valid partition file by running `DfamPartition.py`.

`export_dfam.py` is used to build famdb files for Dfam releases. It
can be used in a few ways:

* Taxonomy can be sourced from the database, or from a local dump of the NCBI taxonomy.
* Families can be sourced from the database, from HMM, and/or from EMBL files.

Example: Export all of Dfam.X.Y
```
$ /usr/bin/time ./export_dfam.py --db_partition ./partitions/F.json --from-db mysql://user:pass@host/database Dfam.X.Y 
```

Example: Export only partition N from Dfam.X.Y
```
$ /usr/bin/time ./export_dfam.py --db_partition ./partitions/F.json -p N --from-db mysql://user:pass@host/database Dfam.X.Y 
```

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
