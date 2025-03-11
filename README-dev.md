# FamDB README for Developers

## Software Structure

### `famdb_classes.py`
#### FamDBLeaf
The basic file for storing Dfam data. Provides methods for writing and retrieving data to `.h5` files.

Data Groups:
* Families - Contains the TE family data elements
* File History - Contains a list of datetimes, each containing a boolean dataset named for the operation performed on the file. False indicates that the operation was interrupted and the file should be considered corrupted.
* Lookup - Contains subdirectories `ByName`, `ByStage` and `ByTaxon` with links to the relevant family elements

#### FamDBRoot
An extension (subclass) of FamDBLeaf that contains additional taxonomy and partition information.

Data Groups:
* Contains all FamDBLeaf data fields and functions.
* Taxonomy - Contains taxonomy structure data relevant to Dfam as a list of node IDs, each with their own data fields: 
    * Parent -  ID of the parent node
    * Children - List of IDs of child nodes
    * Val_Parent - ID of the nearest ancestor node with associated family data
    * Val_Children - List of nearest descendant nodes with assocated family data
    * Partition - The number of the export file containing the family data associated with that taxon
    * TaxaNames - A list of paired strings, where the first item is the name type and the second item is the name for that taxon
* TaxaNames - A serialized JSON string that is parsed into a Taxon ID to Name List lookup map and loaded on initialization for fast name searching
* RepeatPeps - A FASTA file stored as a string, to be provided to RepeatMasker or RepeatModeler when needed

#### FamDB
A class for accessing unified data across a FamDBRoot file and any number of FamDBLeaf files. It verifies that all files in a directory are able to be used together (from the same partition, the same export, contains exactly 1 root file, ect.) and provides functions that collect and collate requested data from multiple files. 

#### `famdb.py`
The python script invoked by the user. Mediates between the user provided arguments and the functions on an instance of FamDB.

### `famdb_globals.py`,`famdb_helper_classes.py` and `famdb_helper_methods.py`
These files contain utility classes and methods that are used by the previous famdb scripts.

### `famdb_data_loaders.py`
This script is used by `export_dfam.py` to read data during export.

### `export_dfam.py`
This script has been moved to an internal Server library, since it interfaces directly with the Dfam database.

### Summplemental.embl
An EMBL file of additional sequencing artefact data not found in Dfam, but necessary for RepeatMasker.

### RepeatPeps.lib
An additional file that is used by RepeatMasker and RepeatModeler.

## Creating famdb files

Before exporting to FamDB be sure that there is a valid partition file by running `~/Server/dfam_partition.py`.

`export_dfam.py` is used to build famdb files for Dfam releases. It
can be used in a few ways:

* Taxonomy can be sourced from the database, or from a local dump of the NCBI taxonomy.
* Families can be sourced from the database, from HMM, and/or from EMBL files.

Example: Export all of Dfam.X.Y
```
$ /usr/bin/time python3 ~/Server/export_dfam.py --from-embl ~/FamDB/Supplemental.embl --repeat-peps ~/FamDB/RepeatPeps.lib -c ~/Conf/dfam.conf --db-partition ~/partitions/F_runlabel_X.Y.json dfam_X.Y &> export.log

```

Example: Export only partition N from Dfam.X.Y
```
$ $ /usr/bin/time python3 ~/Server/export_dfam.py --from-embl ~/FamDB/Supplemental.embl --repeat-peps ~/FamDB/RepeatPeps.lib -c ~/Conf/dfam.conf --db-partition ~/partitions/F_runlabel_X.Y.json -p N dfam_X.Y &> export.log 
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


#### Untested as of FamDB 2.0
Example: build a famdb file from a frozen Dfam release.
```
$ /usr/bin/time ~/export_dfam.py --from-db mysql://user:pass@host/database --from-embl Supplemental.embl --count-taxa-in extra_taxa.txt Dfam_curatedonly.h5
$ /usr/bin/time ~/export_dfam.py --from-db mysql://user:pass@host/database -r --from-embl Supplemental.embl --count-taxa-in extra_taxa.txt Dfam.h5
```

Example: build a famdb file from an HMM file

```
$ /usr/bin/time ~/export_dfam.py --from-tax-dump /path/to/taxonomy --from-hmm=families.hmm --db-version=0.1 custom_hmms.h5
```