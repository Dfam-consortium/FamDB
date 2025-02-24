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

Each installation comprises a required root file as well as a number of optional leaf files. The root file contains data for the higher levels of the taxonomy tree, data for less represented taxa (Fungi, Amoebas), and data for highly studied taxa (Mammals). The leaf files contain data for related taxa as shown in the table below.

The current partitions are:
 Number | Name | Description | Root Taxon ID | File Size | Required 
:---: | :---: | :---: | :---: | :---: | :---: 
 0 | Root | Mammals, Microbes, Fungi, Jellies, & Sponges | 1 | 71Gb | * 
 1 | Obtectomera | Moths & Butterflies | 104431 | 125Gb | |
 2 | Euteleosteomorpha | Bony Fish | 1489388 | 118Gb | 
 3 | Sarcopterygii | Reptiles, Amphibians, & Coelacanths | 8287 | 90Gb | 
 4 | Diptera | Flies | 7147 | 87Gb | 
 5 | Viridiplantae | Plants | 33090 | 72Gb | 
 6 | Deuterostomia | Other Fish & Echinoderms | 33511 | 69Gb | 
 7 | Hymenoptera | Wasps, Bees, & Ants | 7399 | 63Gb | 
 8 | Ecdysozoa | Other Arthropods & Roundworms | 1206794 | 126Gb | 


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