### family
```
usage: famdb.py family [-h] [-f <format>] accession

Retrieve details of a single family.

positional arguments:
  accession             the accession of the family to be retrieved

optional arguments:
  -h, --help            show this help message and exit
  -f <format>, --format <format>
                        choose output format.

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
Prints a single family given by the family accession.

`famdb.py -i ./dfam family [-f <format>] <acc>`

There are many formats to choose from:

  * `summary` (default): A human-readable summary format. Currently includes accession, name, classification, and length.
  ```
  $ famdb.py -i ./dfam family DF000000001

  DF000000001.4 'MIR': root;Interspersed_Repeat;Transposable_Element;Class_I_Retrotransposition;LINE-dependent_Retroposon;SINE;tRNA_Promoter;MIR-core;L2-end len=262
  ```
  * `hmm`: The family's HMM, including some additional metadata such as species and RepeatMasker classification.
  * `hmm_species`: Same as `hmm`, but with a species-specific TH line extracted into the GA/TC/NC values. This format is only useful for the `families` command when querying within a species for which such thresholds have been determined.
  ```
  $ famdb.py -i ./dfam family -f fasta_name DF000000001

  HMMER3/f [3.1b2 | February 2015]
  NAME  MIR
  ACC   DF000000001.4
  DESC  MIR (Mammalian-wide Interspersed Repeat)
  LENG  262
  MAXL  426
  ...
  NC    32.86;
  TH    TaxId:9606; TaxName:Homo sapiens; GA:9.20; TC:32.13; NC:9.15; fdr:0.002;
  TH    TaxId:10090; TaxName:Mus musculus; GA:9.95; TC:31.90; NC:9.90; fdr:0.002;
  TH    TaxId:185453; TaxName:Chrysochloris asiatica; GA:12.80; TC:32.52; NC:12.75; fdr:0.002;
  ...
  CC    MIR is a pan-mammalian SINE with a 5' end derived from a tRNA, a central
  CC    deeply-conserved CORE region [5], and a 3' terminal ~55bp related to an
  CC    L2 LINE.
  CC    RepeatMasker Annotations:
  CC         Type: SINE
  CC         SubType: MIR
  CC         Species: Mammalia
  CC         SearchStages: 40,60,65
  CC         BufferStages: 50[1-262]
  STATS LOCAL MSV      -10.5531  0.70202
  STATS LOCAL VITERBI  -11.4974  0.70202
  STATS LOCAL FORWARD   -4.5297  0.70202
  HMM          A        C        G        T   
            m->m     m->i     m->d     i->m     i->i     d->m     d->d
  COMPO   1.24875  1.66138  1.53211  1.18033
          1.38629  1.38629  1.38629  1.38629
          0.00054  8.21659  8.21659  1.46634  0.26236  0.00000        *
      1   0.02228  5.13440  4.65519  5.01551      1 A x - -
          1.38629  1.38629  1.38629  1.38629
          0.01658  4.80123  4.80123  1.46634  0.26236  1.09861  0.40547
      2   4.53771  0.10078  4.79318  2.56542      2 C x - -
          1.38629  1.38629  1.38629  1.38629
          0.01215  5.10984  5.10984  1.46634  0.26236  1.09861  0.40547
      3   0.05707  4.17876  4.49080  3.54240      3 A x - -
          1.38629  1.38629  1.38629  1.38629
          0.01118  5.19204  5.19204  1.46634  0.26236  1.09861  0.40547
  ...
  //
  ```
  * `fasta_name`: FASTA, with the following header format: `>MIR @Mammalia [S:40,60,65]`
  ```
  $ famdb.py -i ./dfam family -f fasta_name DF000000001

  >MIR @Mammalia [S:40,60,65]
  ACAGTATAGCATAGTGGTTAAGAGCACGGGCTCTGGAGCCAGACTGCCTGGGTTCGAATC
  CCGGCTCTGCCACTTACTAGCTGTGTGACCTTGGGCAAGTTACTTAACCTCTCTGTGCCT
  CAGTTTCCTCATCTGTAAAATGGGGATAATAATAGTACCTACCTCATAGGGTTGTTGTGA
  GGATTAAATGAGTTAATACATGTAAAGCGCTTAGAACAGTGCCTGGCACATAGTAAGCGC
  TCAATAAATGTTAGCTATTATT
  ```
  * `fasta_acc`: FASTA, with the following header format: `>DF0000001.4 @Mammalia [S:40,60,65]`
  ```
  $ famdb.py -i ./dfam family -f fasta_acc DF000000001

  >DF000000001.4 name=MIR @Mammalia [S:40,60,65]
  ACAGTATAGCATAGTGGTTAAGAGCACGGGCTCTGGAGCCAGACTGCCTGGGTTCGAATC
  CCGGCTCTGCCACTTACTAGCTGTGTGACCTTGGGCAAGTTACTTAACCTCTCTGTGCCT
  CAGTTTCCTCATCTGTAAAATGGGGATAATAATAGTACCTACCTCATAGGGTTGTTGTGA
  GGATTAAATGAGTTAATACATGTAAAGCGCTTAGAACAGTGCCTGGCACATAGTAAGCGC
  TCAATAAATGTTAGCTATTATT
  ```
  * `embl`: EMBL, including all metadata and the consensus sequence.
  * `embl_meta`: Same as `embl`, but with only the metadata included.
  * `embl_seq`: Same as `embl`, but with only the sequences included.
```
$ famdb.py -i ./dfam family -f embl DF000000001

ID   DF000000001; SV 4; linear; DNA; STD; UNC; 262 BP.
NM   MIR
XX
AC   DF000000001;
XX
DE   MIR (Mammalian-wide Interspersed Repeat)
XX
DR   Repbase; MIR.
XX
KW   SINE/MIR.
XX
OS   Mammalia
OC   root; cellular organisms; Eukaryota; Opisthokonta; Metazoa; Eumetazoa;
OC   Bilateria; Deuterostomia; Chordata; Craniata <chordates>; Vertebrata
OC   <vertebrates>; Gnathostomata <vertebrates>; Teleostomi; Euteleostomi;
OC   Sarcopterygii; Dipnotetrapodomorpha; Tetrapoda; Amniota.
XX
RN   [1] (bases 1 to 262)
RA   Degen SJ, Davie EW;
RT   Nucleotide sequence of the gene for human prothrombin.
RL   Biochemistry 1987;26:6165-6177
XX
RN   [2] (bases 1 to 262)
RA   Donehower LA, Slagle BL, Wilde M, Darlington G, Butel JS;
RT   Identification of a conserved sequence in the noncoding regions of many
RT   human genes.
RL   Nucleic Acids Res 1989;17:699-710
XX
RN   [3] (bases 1 to 262)
RA   Jurka J, Zietkiewicz E, Labuda D;
RT   Ubiquitous mammalian-wide interspersed repeats (MIRs) are molecular
RT   fossils from the mesozoic era.
RL   Nucleic Acids Res 1995;23:170-175
XX
RN   [4] (bases 1 to 262)
RA   Smit AF, Riggs AD;
RT   MIRs are classic, tRNA-derived SINEs that amplified before the mammalian
RT   radiation.
RL   Nucleic Acids Res 1995;23:98-102
XX
RN   [5] (bases 1 to 262)
RA   Gilbert N, Labuda D;
RT   Evolutionary inventions and continuity of CORE-SINEs in mammals.
RL   J Mol Biol 2000;298:365-377
XX
CC   MIR is a pan-mammalian SINE with a 5' end derived from a tRNA, a central
CC   deeply-conserved CORE region [5], and a 3' terminal ~55bp related to an
CC   L2 LINE.
CC
CC   RepeatMasker Annotations:
CC        Type: SINE
CC        SubType: MIR
CC        Species: Mammalia
CC        SearchStages: 40,60,65
CC        BufferStages: 50[1-262]
XX
//
```