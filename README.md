# FamDB

## Getting Started

`pip3 install --user h5py`
`./famdb.py -h`

## Usage

General usage is as follows:

`famdb.py -i dfam.h5 <command>`

where `<command>` is one of `names`, `lineage`, `families`, or `family`.

### names

Searches the taxonomy database for species names and prints all known names for
any matches. The output is human-readable ("pretty") by default but can also be
in JSON format. Only the JSON format is intended for parsing by scripts.

`famdb.py -i dfam.h5 names [-f json] <term>`

`term` can be a taxonomy identifier number or part of a species/clade name.
This also applies to other commands that take a taxonomy "term", including
`lineage` and `families`.

If the `term` is not found, similar-sounding names will be suggested.

### lineage

Prints the lineage tree for a species with line drawing characters.  The tree
includes the count of families assigned to each clade.  Optionally includes
ancestors (`-a`) and/or descendants (`-d`); by default only the exact taxon
specified is included.

`famdb.py -i dfam.h5 lineage [-a] [-d] [-f semicolon] <term>`

The semicolon-delimited format does not include the tree drawing and  is more
suitable for parsing.

### family

Prints a single family given the family accession.

`famdb.py -i dfam.h5 family [-f <format>] <acc>`

There are many formats to choose from:

  * `summary` (default): A human-readable format. Currently includes
    accession, name, classification, and length.
  * `hmm`: The HMM, including some additional metadata such as species and
    RepeatMasker classification.
  * `hmm_species`: Same as `hmm`, but with a species-specific TH line extracted
    into the GA/TC/NC values. This format only makes sense for the `families`
    command when looking at a specific species (not any arbitrary clade).
  * `fasta_name`: FASTA, with this header format:
    `>MIR#SINE/MIR @Mammalia [S:40,60,65]`
  * `fasta_acc`: FASTA, with this header format:
    `>DF0000001.4#SINE/MIR @Mammalia [S:40,60,65]`
  * `embl`: EMBL, including all metadata and the DNA sequence.
  * `embl_meta`: Same as `embl`, but with only the metadata included.
  * `embl_seq`: Same as `embl`, but with only the sequences included.


### families

The `families` command takes a taxonomy `term`, and prints all families
assigned to that clade (optionally including ancestors and/or descendants) with
optional additional filters.

`famdb.py -i dfam.h5 families [-a] [-d]
  [--stage <st>] [--class <cl>] [--name <name>]
  [-f <format>] <term>`

`[-a]`, `[-d]` include ancestors/descendants as with lineage.
The formats for `[-f <format>]` are the same as for `family`.

Filters:
  * `--stage <st>`: Includes only families in the given search or buffer stage.
    Search stages and buffer stages are a concept specific to RepeatMasker.
  * `--name <name>`: Includes only families whose name starts with the search
    term.
  * `--class <class>`: Includes only families whose class starts with the
    specified *repeatmasker type*.
