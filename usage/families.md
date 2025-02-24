### families
```
usage: famdb.py families [-h] [-a] [-d] [--stage STAGE] [--class REPEAT_TYPE]
                         [--name NAME] [-u] [-c] [-f <format>]
                         [--add-reverse-complement] [--include-class-in-name]
                         [--require-general-threshold]
                         term [term ...]

Retrieve the families associated with a given clade, optionally filtered by additional criteria

positional arguments:
  term                  search term. Can be an NCBI taxonomy identifier or an
                        unambiguous scientific or common name

optional arguments:
  -h, --help            show this help message and exit
  -a, --ancestors       include all ancestors of the given clade
  -d, --descendants     include all descendants of the given clade
  --stage STAGE         include only families that should be searched in the
                        given stage
  --class REPEAT_TYPE   include only families that have the specified repeat
                        Type/SubType
  --name NAME           include only families whose name begins with this
                        search term
  -u, --uncurated       include only 'uncurated' families (i.e. named
                        DRXXXXXXXXX)
  -c, --curated         include only 'curated' families (i.e. not named
                        DFXXXXXXXXX)
  -f <format>, --format <format>
                        choose output format.
  --add-reverse-complement
                        include a reverse-complemented copy of each matching
                        family; only suppported for fasta formats
  --include-class-in-name
                        include the RepeatMasker type/subtype after the name
                        (e.g. HERV16#LTR/ERVL); only supported for hmm and
                        fasta formats
  --require-general-threshold
                        skip families missing general thresholds (and log
                        their accessions at the debug log level)

Supported formats:
  * 'summary'     : (default) A human-readable summary format. Currently includes
                    accession, name, classification, and length.

  * 'hmm'         : The family's HMM, including some additional metadata such as
                    species and RepeatMasker classification.
  * 'hmm_species' : Same as 'hmm', but with a species-specific TH line extracted
                    into the GA/TC/NC values. This format is only useful for the
                    families command when querying within a species for which such
                    thresholds have been determined.

  * 'fasta_name'  : FASTA, with the following header format:
                    >MIR @Mammalia [S:40,60,65]
  * 'fasta_acc'   : FASTA, with the following header format:
                    >DF0000001.4 @Mammalia [S:40,60,65]

  * 'embl'        : EMBL, including all metadata and the consensus sequence.
  * 'embl_meta'   : Same as 'embl', but with only the metadata included.
  * 'embl_seq'    : Same as 'embl', but with only the sequences included.
```
The `families` command takes a taxonomy `term` and prints all families assigned
to that clade (optionally including ancestors and/or descendants) with optional
additional filters.

`famdb.py -i ./dfam families [-a] [-d]
  [--stage <st>] [--class <cl>] [--name <name>] [--curated]
  [-f <format>] [--add-reverse-complement] [--include-class-in-name]
  <term>`

`-a`, `-d` include ancestors/descendants as with the `lineage` command.
The formats for `-f <format>` are the same as for the `family` command.

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
$ famdb.py -i ./dfam families hominid

Dfam - A database of transposable element (TE) sequence alignments and HMMs
Copyright (C) 2023 The Dfam consortium.

Release: Dfam_3.8
Date   : 2023-11-14

This database is free; you can redistribute it and/or modify it
as you wish, under the terms of the CC0 1.0 license, a
'no copyright' license:

The Dfam consortium has dedicated the work to the public domain, waiving
all rights to the work worldwide under copyright law, including all related
and neighboring rights, to the extent allowed by law.

You can copy, modify, distribute and perform the work, even for
commercial purposes, all without asking permission.
See Other Information below.

Other Information

o In no way are the patent or trademark rights of any person affected by
  CC0, nor are the rights that other persons may have in the work or in how
  the work is used, such as publicity or privacy rights.
o Makes no warranties about the work, and disclaims liability for all uses of the
  work, to the fullest extent permitted by applicable law.
o When using or citing the work, you should not imply endorsement by the Dfam consortium.

You may also obtain a copy of the CC0 license here:
http://creativecommons.org/publicdomain/zero/1.0/legalcode

DF000000589.6 'LTR7Y': root;Interspersed_Repeat;Transposable_Element;Class_I_Retrotransposition;Retrotransposon;Long_Terminal_Repeat_Element;Gypsy-ERV;Retroviridae;Orthoretrovirinae;ERV1 len=464
DF000001068.4 'SVA_B': root;Interspersed_Repeat;Transposable_Element;Class_I_Retrotransposition;LINE-dependent_Retroposon;Lacking_Small_RNA_pol_III_Promoter;L1-dependent;SVA len=1383
DF000001069.4 'SVA_C': root;Interspersed_Repeat;Transposable_Element;Class_I_Retrotransposition;LINE-dependent_Retroposon;Lacking_Small_RNA_pol_III_Promoter;L1-dependent;SVA len=1384
DF000001070.4 'SVA_D': root;Interspersed_Repeat;Transposable_Element;Class_I_Retrotransposition;LINE-dependent_Retroposon;Lacking_Small_RNA_pol_III_Promoter;L1-dependent;SVA len=1386
DF000001174.2 'AluYe6': root;Interspersed_Repeat;Transposable_Element;Class_I_Retrotransposition;LINE-dependent_Retroposon;SINE;7SL-RNA_Promoter;No-core;L1-dependent;Alu len=310
DF003440070.2 'LTR7B0': root;Interspersed_Repeat;Transposable_Element;Class_I_Retrotransposition;Retrotransposon;Long_Terminal_Repeat_Element;Gypsy-ERV;Retroviridae;Orthoretrovirinae;ERV1 len=448
```

```
$ famdb.py -i ./dfam families --name SVA -f fasta_acc --include-class-in-name hominid

>DF000001068.4#Retroposon/SVA name=SVA_B @Hominidae [S:40,50]
CTCTCCCTCTCCCTCTCCCTCTCCCTCTCCCTCTCCCTCTCCCTNTCCCCTCTTTCCACG
GTCTCCCTCTGATGCCGAGCCGAGGCTGGACTGTACTGCCGCCATCTCGGCTCACTGCAA
CCTCCCTGCCTGATTCTCCTGCCTCAGCCTGCCGAGTGCCTGGGATTGCAGGCGCGCGCC
GCCACGCCTGACTGGTTTTCGTATTTTTTGGTGGAGACGGGGTTTCGCCGTGTTGGCCGG
GCTGGTCTCCAGCTCCTGACCGCGAGTGATCTGCCNGCCTCGGCCTCCCGAGGTGCCGGG
ATTGCAGACGGAGTCTCGCTCACTCAGTGCTCAATGTTGCCCAGGCTGGAGTGCAGTGGC
GTGATCTCGGCTCGCTACAACCTCCACCTCCCAGCCGCCTGCCTTGGCCTCCCAAAGTGC
CGAGATTGCAGCCTCTGCCCGGCCGCCACCCCGTCTGGGAAGTGAGGAGCGTCTCTGCCT
GGCCGCCCATCGTCTGGGATGTGAGGAGCCCCTCTGCCCGGCCGCCCAGTCTGGGAAGTG
AGGAGCGCCTCTTCCCGGCCGCCATCCCGTCTGGGAAGTGAGGAGCGTCTCTGCCCGGCC
GCCCATCGTCTGGGATGTGGGGAGCGCCTCTGCCCCGCCGCCCCGTCTGGGANGTGAGGA
GCGCCTCTGCCCGGCCAGCCGCCCCGTCTGGGAGGTGAGGAGGTCAGCCCCCCGCCCGGC
CAGCCGCCCCGTCCGGGAGGAGGTGGGGGGNNCAGCCCCCCGCCCGGCCAGCCGCCCCGT
CCGGGAGGTGGGGGGCGCCTCTGCCCGGCCGCCCCGTCTGGGAAGTGAGGAGCCCCTCTG
CCCGGCCGCCACCCCGTCTGGGAGGTGTACCCAACAGCTCATTGAGAACGGGCCATGATG
ACGATGGCGGTTTTGTCGAATAGAAAAGGGGGAAATGTGGGGAAAAGAAAGAGAGATCAG
ATTGTTACTGTGTCTGTGTAGAAAGAAGTAGACATAGGAGACTCCATTTTGTTCTGTACT
AAGAAAAATTCTTCTGCCTTGGGATGCTGTTAATCTATAACCTTACCCCCAACCCCGTGC
TCTCTGAAACATGTGCTGTGTCCACTCAGGGTTAAATGGATTAAGGGCGGTGCAAGATGT
GCTTTGTTAAACAGATGCTTGAAGGCAGCATGCTCGTTAAGAGTCATCACCACTCCCTAA
TCTCAAGTACCCAGGGACACAAACACTGCGGAAGGCCGCAGGGTCCTCTGCCTAGGAAAA
CCAGAGACCCTTGTTCACATGTTTATCTGCTGACCTTCCCTCCACTATTGTCCTATGACC
CTGCCAAATCCCCCTCTCCGAGAAACACCCAAGAATGATCAATAAATACTAAAAAAAAAA
AAA
>DF000001069.4#Retroposon/SVA name=SVA_C @Hominidae [S:40,50]
CTCTCCCTCTCCCTCTCCCTCTCCCTCTCCCTCTCCCTCTCCCTCTCCCCTCTTTCCACG
GTCTCCCTCTGATGCCGAGCCGAAGCTGGACTGTACTGCCGCCATCTCGGCTCACTGCAA
CCTCCCTGCCTGATTCTCCTGCCTCAGCCTGCCGAGTGCCTGCGATTGCAGGCGCGCGCC
GCCACGCCTGACTGGTTTTCGTATTTTTTTGGTGGAGACGGGGTTTCGCTGTGTTGGCCG
GGCTGGTCTCCAGCTCCTAACCGCGAGTGATCCGCCAGCCTCGGCCTCCCGAGGTGCCGG
GATTGCAGACGGAGTCTCGTTCACTCAGTGCTCAATGTTGCCCAGGCTGGAGTGCAGTGG
CGTGATCTCGGCTCGCTACAACCTCCACCTCCCAGCCGCCTGCCTTGGCCTCCCAAAGTG
CCGAGATTGCAGCCTCTGCCCGGCCGCCACCCCGTCTGGGAAGTGAGGAGCGTCTCTGCC
TGGCCGCCCATCGTCTGGGATGTGAGGAGCCCCTCTGCCCGGCTGCCCAGTCTGGGAAGT
GAGGAGCGCCTCTTCCCGGCCGCCATCCCGTCTAGGAAGTGAGGAGCGTCTCTGCCCGGC
CGCCCATCGTCTGAGATGTGGGGAGCGCCTCTGCCCCGCCGCCCCGTCTGGGATGTGAGG
AGCGCCTCTGCCCGGCCAGCCGCCCCGTCTGGGAGGTGGGGGGGTCAGCCCCCCGCCCGG
CCAGCCGCCCCGTCCGGGAGGAGGTGGGGGGGTCAGCCCCCCGCCCGGCCAGCCGCCCCG
TCCGGGAGGTGGGGGGCGCCTCTGCCCGGCCGCCCCTTCTGGGAAGTGAGGAGCCCCTCT
GCCCGGCCGCCACCCCGTCTGGGAGGTGTACCCAACAGCTCATTGAGAACGGGCCATGAT
GACGATGGCGGTTTTGTCGAATAGAAAAGGGGGAAATGTGGGGAAAAGATAGAGAAATCA
GATTGTTGCTGTGTCTGTGTAGAAAGAAGTAGACATGGGAGACTCCATTTTGTTCTGTAC
TAAGAAAAATTCTTCTGCCTTGGGATGCTGTTGATCTATGACCTTACCCCCAACCCNGTG
CTCTCTGAAACATGTGCTGTGTCCACTCAGGGTTAAATGGATTAAGGGCGGTGCAAGATG
TGCTTTGTTAAACAGATGCTTGAAGGCAGCATGCTCGTTAAGAGTCATCACCACTCCCTA
ATCTCAAGTACCCAGGGACACAAACACTGCGGAAGGCCGCAGGGTCCTCTGCCTAGGAAA
ACCAGAGACCTTTGTTCACTTGTTTATCTGCTGACCTTCCCTCCACTATTGTCCTATGAC
CCTGCCAAATCCCCCTCTGCGAGAAACACCCAAGAATGATCAATAAAAAAAAAAAAAAAA
AAAA
>DF000001070.4#Retroposon/SVA name=SVA_D @Hominidae [S:40,50]
CTCTCCCTCTCCCTCTCCCTCTCCCTCTCCCTCTCCCTCTCCCTCTCCCCTCTTTCCACG
GTCTCCCTCTGATGCCGAGCCGAAGCTGGACTGTACTGCTGCCATCTCGGCTCACTGCAA
CCTCCCTGCCTGATTCTCCTGCCTCAGCCTGCCGAGTGCCTGCGATTGCAGGCGCGCGCC
GCCACGCCTGACTGGTTTTCGTATTTTTTTGGTGGAGACGGGGTTTCGCTGTGTTGGCCG
GGCTGGTCTCCAGCTCCTAACCGCGAGTGATCCGCCAGCCTCGGCCTCCCGAGGTGCCGG
GATTGCAGACGGAGTCTCGTTCACTCAGTGCTCAATGGTGCCCAGGCTGGAGTGCAGTGG
CGTGATCTCGGCTCGCTACAACCTCCACCTCCCAGCCGCCTGCCTTGGCCTCCCAAAGTG
CCGAGATTGCAGCCTCTGCCCGGCCGCCACCCCGTCTGGGAAGTGAGGAGCGTCTCTGCC
CGGCCGCCCATCGTCTGGGATGTGAGGAGCCCCTCTGCCCGGCCGCCCAGTCTGGGAAGT
GAGGAGCGCCTCTGCCCGGCCGCCATCCCGTCTAGGAAGTGAGGAGCGTCTCTGCCCGGC
CGCCCATCGTCTGAGATGTGGGGAGCGCCTCTGCCCCGCCGCCCCGTCTGGGATGTGAGG
AGCGCCTCTGCCCGGCCAGCCGCCCCGTCCGGGAGGTGGGGGGGTCAGCCCCCCGCCCGG
CCAGCCGCCCCGTCCGGGAGGAGGTGGGGGGGTCAGCCCCCCGCCCGGCCAGCCGCCCCG
TCCGGGAGGTGAGGGGCGCCTCTGCCCGGCCGCCCCTACTGGGAAGTGAGGAGCCCCTCT
GCCCGGCCACCACCCCGTCTGGGAGGTGTACCCAACAGCTCATTGAGAACGGGCCATGAT
GACAATGGCGGTTTTGTGGAATAGAAAGGGGGGAAAGGTGGGGAAAAGATTGAGAAATCG
GATGGTTGCCGTGTCTGTGTAGAAAGAAGTAGACATGGGAGACTTTTCATTTTGTTCTGT
ACTAAGAAAAATTCTTCTGCCTTGGGATCCTGTTGATCTGTGACCTTACCCCCAACCCTG
TGCTCTCTGAAACATGTGCTGTGTCCACTCAGGGTTAAATGGATTAAGGGCGGTGCAAGA
TGTGCTTTGTTAAACAGATGCTTGAAGGCAGCATGCTCGTTAAGAGTCATCACCACTCCC
TAATCTCAAGTACCCAGGGACACAAACACTGCGGAAGGCCGCAGGGTCCTCTGCCTAGGA
AAACCAGAGACCTTTGTTCACTTGTTTATCTGCTGACCTTCCCTCCACTATTGTCCTATG
ACCCTGCCAAATCCCCCTCTGCGAGAAACACCCAAGAATGATCAATAAAAAAAAAAAAAA
AAAAAA
```