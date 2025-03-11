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

FamDB can also be downloaded separately. At this time, only the file famdb.py is
needed. The latest development version is located here:
<https://raw.githubusercontent.com/Dfam-consortium/FamDB/master/famdb.py>

## Usage

General usage is as follows:

`famdb.py -i <directory> <command>`

where `<directory>` is the folder holding the .h5 export files
where `<command>` is one of `info`, `names`, `lineage`, `families`, or `family`.

### info

Prints general information and statistics about the database, such as title,
version, date, and count of consensus sequences and HMMs in the database.

### names

Searches the taxonomy database for species names and prints all known names for
any matches. The output is human-readable ("pretty") by default but can also be
in JSON format. The JSON format is intended for parsing by scripts; the pretty
format is too unstructured to parse reliably.

`famdb.py -i ./dfam names [-f json] <term>`

`term` can be a taxonomy identifier number or part of a species/clade name.
In this example the FamDB files are stored in a directory called 'dfam' in 
the current working directory.  RepeatMasker looks for them in its "Library/famdb"
directory by default.

Exact matches are distinguished from non-exact matches. For example:

```
$ famdb.py -i ./dfam names rattus

Exact Matches
=============
10114 rat <Rattus> (common name), rats <Rattus> (common name), Rattus
(scientific name)

Non-exact Matches
=================
10115 Cape York rat (common name), mottle-tailed rat (genbank common name),
Rattus leucopus (scientific name)
10116 brown rat (common name), Buffalo rat (includes), laboratory rat
(includes), Norway rat (genbank common name), rat <Rattus norvegicus> (common
name), rats <Rattus norvegicus> (common name), Rattus norvegicus (scientific
name), Rattus PC12 clone IS (includes), Rattus sp. strain Wistar (includes),
Sprague-Dawley rat (includes), Wistar rats (includes), zitter rats (includes)
10117 black rat (genbank common name), house rat (common name), Rattus rattoides
<Rattus rattus> (synonym), Rattus rattoides (Pictet & Pictet, 1844) (authority),
Rattus rattus (scientific name), Rattus rattus (Linnaeus, 1758) (authority),
Rattus wroughtoni (synonym), Rattus wroughtoni Hinton, 1919 (authority), roof
rat (common name)
(...)
```

Other commands that take a taxonomy "term", including `lineage` and `families`,
generally use the same search system as the `names` command. Most commands
require a single exact match, or if there are no exact matches a single partial
match. This requirement provides some leniency in name choice without allowing
ambiguities.

If there are no matches for `term`, similar-sounding names will be suggested.

### lineage

Prints the lineage tree for a species or clade with line drawing characters. The
tree includes the number of families assigned to each clade. The options `-a`
(ancestors) and/or `-d` (descendants) can be added to include ancestors,
descendants, or both, as desired.

`famdb.py -i ./dfam lineage [-a] [-d] [-f semicolon|totals] <term>`

The semicolon-delimited format does not include the tree drawing and is more
suitable for parsing. The `totals` format prints the number of ancestral
and of lineage-specific repeats known for the given species.  In the example
below the count of families specifically assigned to each taxon is shown in
brackets.  The number in parentheses indicates which partition of FamDB contains
the data for that taxon and its descendants.

```
$ famdb.py -i ./dfam lineage -ad humans

1 root(0) [0]
└─131567 cellular organisms(0) [0]
  └─2759 Eukaryota(0) [0]
    └─33154 Opisthokonta(0) [0]
      └─33208 Metazoa(0) [5]
        └─6072 Eumetazoa(0) [0]
          └─33213 Bilateria(0) [0]
            └─33511 Deuterostomia(0) [0]
              └─7711 Chordata(0) [0]
                └─89593 Craniata <chordates>(0) [0]
                  └─7742 Vertebrata <vertebrates>(0) [67]
                    └─7776 Gnathostomata <vertebrates>(0) [0]
                      └─117570 Teleostomi(0) [0]
                        └─117571 Euteleostomi(0) [1]
                          └─8287 Sarcopterygii(0) [0]
                            └─1338369 Dipnotetrapodomorpha(0) [0]
                              └─32523 Tetrapoda(0) [19]
                                └─32524 Amniota(0) [100]
                                  └─40674 Mammalia(0) [68]
                                    └─32525 Theria <mammals>(0) [69]
                                      └─9347 Eutheria(0) [387]
                                        └─1437010 Boreoeutheria(0) [40]
                                          └─314146 Euarchontoglires(0) [44]
                                            └─9443 Primates(0) [140]
                                              └─376913 Haplorrhini(0) [199]
                                                └─314293 Simiiformes(0) [56]
                                                  └─9526 Catarrhini(0) [104]
                                                    └─314295 Hominoidea(0) [23]
                                                      └─9604 Hominidae(0) [6]
                                                        └─207598 Homininae(0) [14]
                                                          └─9605 Homo(0) [0]
                                                            └─9606 Homo sapiens(0) [52]
```

### family

Prints a single family given by the family accession.

`famdb.py -i ./dfam family [-f <format>] <acc>`

There are many formats to choose from:

  * `summary` (default): A human-readable summary format. Currently includes
    accession, name, classification, and length.
  * `hmm`: The family's HMM, including some additional metadata such as species
    and RepeatMasker classification.
  * `hmm_species`: Same as `hmm`, but with a species-specific TH line extracted
    into the GA/TC/NC values. This format is only useful for the `families`
    command when querying within a species for which such thresholds have been
    determined.
  * `fasta_name`: FASTA, with the following header format:
    `>MIR @Mammalia [S:40,60,65]`
  * `fasta_acc`: FASTA, with the following header format:
    `>DF0000001.4 @Mammalia [S:40,60,65]`
  * `embl`: EMBL, including all metadata and the consensus sequence.
  * `embl_meta`: Same as `embl`, but with only the metadata included.
  * `embl_seq`: Same as `embl`, but with only the sequences included.

```
$ famdb.py -i ./dfam family -f fasta_name DF0000001

>MIR @Mammalia [S:40,60,65]
ACAGTATAGCATAGTGGTTAAGAGCACGGGCTCTGGAGCCAGACTGCCTGGGTTCGAATC
CCGGCTCTGCCACTTACTAGCTGTGTGACCTTGGGCAAGTTACTTAACCTCTCTGTGCCT
CAGTTTCCTCATCTGTAAAATGGGGATAATAATAGTACCTACCTCATAGGGTTGTTGTGA
GGATTAAATGAGTTAATACATGTAAAGCGCTTAGAACAGTGCCTGGCACATAGTAAGCGC
TCAATAAATGTTAGCTATTATT
```

### families

The `families` command takes a taxonomy `term` and prints all families assigned
to that clade (optionally including ancestors and/or descendants) with optional
additional filters.

`famdb.py -i ./dfam families [-a] [-d]
  [--stage <st>] [--class <cl>] [--name <name>] [--curated]
  [-f <format>] [--add-reverse-complement] [--include-class-in-name]
  <term>`

`[-a]`, `[-d]` include ancestors/descendants as with lineage.
The formats for `[-f <format>]` are the same as for `family`.

Filters:
  * `--stage <st>`: Includes only families in the given search or buffer stage.
    Search stages and buffer stages are a concept specific to RepeatMasker.
  * `--class <class>`: Includes only families whose class starts with the
    specified repeat type, according to the RepeatMasker nomenclature.
  * `--name <name>`: Includes only families whose name starts with the search
    term.
  * `--curated`: Excludes uncurated entires (accession `DR_______`).

Output options:
  * `--add-reverse-complement` (`fasta` formats only): Adds a second copy of
    each family found in the reverse complement; used internally by
    RepeatMasker.
  * `--include-class-in-name` (`fasta` and `hmm` formats only): Includes the
    RepeatMasker type/subtype in the family name, e.g. `HERV16#LTR/ERVL`.

```
$ famdb.py -i ./dfam families -f embl_seq -a human
```
