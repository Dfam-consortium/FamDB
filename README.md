# FamDB

## Overview

FamDB is a modular HDF5-based export format and query tool developed for offline access
to the [Dfam] database of transposable element and repetitive DNA families.
FamDB stores family sequence models (profile HMMs, and consensus sequences),
metadata including:

 * Family names, aliases, description
 * Classification
 * Taxa
 * Citations and attribution.

In addition, FamDB stores a subset of the NCBI Taxonomy relevant to the family
taxa represented in the file, facilitating quick extraction of
species/clade-specific family libraries.  The query tool provides options for
exporting search results in a variety of common formats including EMBL, FASTA,
and HMMER HMM format.  At this time FamDB is intended for use as a "read-only"
data store by tools such as [RepeatMasker] as an alternative to unindexed EMBL
or HMM files.

[Dfam]: https://www.dfam.org/
[RepeatMasker]: http://www.repeatmasker.org/

## Installation/Setup
FamDB files follow a simple hierarchical structure based on the NCBI taxonomy tree. These files represent partitioned subsets of the Dfam database and contain data for related areas of the taxonomy tree. 

Each installation comprises a required root file as well as a number of optional leaf files. The root file contains data for the highest levels of the taxonomy tree and is required in order to interact with the leaf files. The leaf files contain data for related taxa as shown in the table below.

The current partitions are:
 Number | Name | Description | Root Taxon ID | File Size | Required 
:---: | :---: | :---: | :---: | :---: | :---: 
 0 | Root | | 1 | 0.074Gb | * 
 1 | Brachycera | Flies | 7203 | 73Gb | |
 2 | Archelosauria | Turtles, Birds, & Crocodilians | 1329799 | 66Gb | 
 3 | Hymenoptera | Ants, Bees, & Wasps | 7399 | 60Gb | 
 4 | Otomorpha | Bony Fishes(?) | 186634 | 57Gb | 
 5 | rosids | rosids | 71275 | 57Gb | 
 6 | Viridiplantae | Other Plants | 33090 | 60Gb | 
 7 | Mammalia | Mammals | 40674 | 57Gb | 
 8 | Noctuoidea | Owlet Moths | 37570 | 52Gb | 
 9 | Obtectomera | Other Moths and Butterflies(?) | 104431 | 67Gb |
 10 | Eupercaria | Bony Fishes (?) | 1489922 | 50Gb |
 11 | Ctenosquamata | Bony Fishes (?) | 123367 | 64Gb |
 12 | Vertebrata <vertebrates> | Ancient Fish (?), Other Reptiles | 7742 | 74Gb |
 13 | Coleoptera | Beetles | 7041 | 40Gb |
 14 | Endopterygota | Other Insects (?) | 33392 | 43Gb |
 15 | Protostomia | Roundworms, Non Insect Arthropods, Other inects and worms (?)| 33317 | 70Gb |
 16 | Riboviria | Fungi, Marine Invertebrates, Red Algae, Protists, Viruses | 2559587 | 35Gb |

All FamDB files follow the convention `<export name>.<partition number>.h5` where the root partition is partition 0. All files from the same export should be kept in the same directory with no other exports present. The FamDB software will display a warning if files from different export or partitioning runs are present. The name of the directory containing the FamDB files is passed as an argument to `famdb.py`.

### Dependencies

* [`h5py`], to read and write files in HDF5 format

    ```
    $ pip3 install --user h5py
    ```

[`h5py`]: https://pypi.org/project/h5py/

### famdb.py

RepeatMasker includes a compatible version of famdb.py. This file should
generally not be installed or upgraded manually.

FamDB can also be downloaded separately. The latest development version is located here:
<https://github.com/Dfam-consortium/FamDB/releases/latest>

## Usage
General usage is as follows:

`famdb.py -i <directory> <command>`

where `<directory>` is the folder holding the .h5 export files
where `<command>` is one of `info`, `names`, `lineage`, `families`, or `family`.

See the example files for each command in the `usage` directory.
```
$ famdb.py -h

usage: famdb.py [-h] [-l LOG_LEVEL] [-i DB_DIR]
                {info,names,lineage,families,family,append} ...

This is famdb.py version 2.0.0.

example commands, including the most commonly used options:

  famdb.py [-i DB_DIR] info
    Prints information about the file including database name and date.

  famdb.py [-i DB_DIR] names 'mus' | head
    Prints taxonomy nodes that include 'mus', and the corresponding IDs.
    The IDs and names are stored in the FamDB file, and are based
    on the NCBI taxonomy database (https://www.ncbi.nlm.nih.gov/taxonomy).

  famdb.py [-i DB_DIR] lineage -ad 'Homo sapiens'
  famdb.py [-i DB_DIR] lineage -ad --format totals 9606
    Prints a taxonomic tree including the given clade and optionally ancestors
    and/or descendants, with the number of repeats indicated at each level of
    the hierarchy. With the 'totals' format, prints the number of matching
    ancestral and lineage-specific entries.

  famdb.py [-i DB_DIR] family --format fasta_acc MIR3
    Exports a single family from the database in one of several formats.

  famdb.py [-i DB_DIR] families -f embl_meta -ad --curated 'Drosophila melanogaster'
  famdb.py [-i DB_DIR] families -f hmm -ad --curated --class LTR 7227
    Searches and exports multiple families from the database, in one of several formats.

optional arguments:
  -h, --help            show this help message and exit
  -l LOG_LEVEL, --log_level LOG_LEVEL
  -i DB_DIR, --db_dir DB_DIR
                        specifies the directory to query

subcommands:
  Specifies the kind of query to perform.
  For more information on all the possible options for a command, add the --help option after it:
  famdb.py families --help

  {info,names,lineage,families,family,append}
```