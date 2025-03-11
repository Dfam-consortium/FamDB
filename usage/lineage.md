### lineage
```
usage: famdb.py lineage [-h] [-a] [-d] [-k] [-c] [-u] [-f <format>]
                        term [term ...]

List the taxonomy tree including counts of families at each clade.

positional arguments:
  term                  search term. Can be an NCBI taxonomy identifier or an
                        unambiguous scientific or common name

optional arguments:
  -h, --help            show this help message and exit
  -a, --ancestors       include all ancestors of the given clade
  -d, --descendants     include all descendants of the given clade
  -k, --complete        include taxa without families in output
  -c, --curated         only tabulate curated families ('DF' records)
  -u, --uncurated       only tabulate uncurated families ('DR' records)
  -f <format>, --format <format>
                        choose output format. The default is 'pretty'.
                        'semicolon' is more appropriate for scripts. 'totals'
                        displays the number of ancestral and lineage-specific
                        families found.
```

The `lineage` command prints the lineage tree for a species or clade with line drawing characters. The
tree includes the number of families assigned to each clade. The options `-a`/`--ancestors` and/or `-d`/`--descendants` can be added to include ancestors,
descendants, or both, as desired.

In the example below the count of families specifically assigned to each taxon is shown in brackets.  
The number in parentheses indicates which partition of FamDB contains the data for that taxon and its descendants.

```
$ famdb.py -i ./dfam lineage -ad humans

1 root(0) [9]
└─33208 Metazoa(0) [5]
  └─7742 Vertebrata <vertebrates>(0) [80]
    └─117571 Euteleostomi(0) [1]
      └─32523 Tetrapoda(0) [19]
        └─32524 Amniota(0) [99]
          └─40674 Mammalia(0) [67]
            └─32525 Theria <mammals>(0) [69]
              └─9347 Eutheria(0) [387]
                └─1437010 Boreoeutheria(0) [40]
                  └─314146 Euarchontoglires(0) [44]
                    └─9443 Primates(0) [156]
                      └─376913 Haplorrhini(0) [199]
                        └─314293 Simiiformes(0) [56]
                          └─9526 Catarrhini(0) [104]
                            └─314295 Hominoidea(0) [23]
                              └─9604 Hominidae(0) [6]
                                └─207598 Homininae(0) [14]
                                  └─9605 Homo(0) [0]
                                    └─9606 Homo sapiens(0) [52]
```

Note that the above output does not show every node in the taxonomy tree between 1 and 9606.
To include every node, even if there are no families associated with it, use the `-k` or `--complete` arguement.
```
$ famdb.py -i ./dfam lineage -adk humans

1 root(0) [9]
└─131567 cellular organisms(0) [0]
  └─2759 Eukaryota(0) [0]
    └─33154 Opisthokonta(0) [0]
      └─33208 Metazoa(0) [5]
        └─6072 Eumetazoa(0) [0]
          └─33213 Bilateria(0) [0]
            └─33511 Deuterostomia(0) [0]
              └─7711 Chordata(0) [0]
                └─89593 Craniata <chordates>(0) [0]
                  └─7742 Vertebrata <vertebrates>(0) [80]
                    └─7776 Gnathostomata <vertebrates>(0) [0]
                      └─117570 Teleostomi(0) [0]
                        └─117571 Euteleostomi(0) [1]
                          └─8287 Sarcopterygii(0) [0]
                            └─1338369 Dipnotetrapodomorpha(0) [0]
                              └─32523 Tetrapoda(0) [19]
                                └─32524 Amniota(0) [99]
                                  └─40674 Mammalia(0) [67]
                                    └─32525 Theria <mammals>(0) [69]
                                      └─9347 Eutheria(0) [387]
                                        └─1437010 Boreoeutheria(0) [40]
                                          └─314146 Euarchontoglires(0) [44]
                                            └─9443 Primates(0) [156]
                                              └─376913 Haplorrhini(0) [199]
                                                └─314293 Simiiformes(0) [56]
                                                  └─9526 Catarrhini(0) [104]
                                                    └─314295 Hominoidea(0) [23]
                                                      └─9604 Hominidae(0) [6]
                                                        └─207598 Homininae(0) [14]
                                                          └─9605 Homo(0) [0]
                                                            └─9606 Homo sapiens(0) [52]
```

The `semicolon` format does not include the tree drawing and is more suitable for parsing. It also always includes the `--ancestors` and `--complete` arguements, since the need for a full taxonomic lineage is assumed.
```
$ famdb.py -i ./dfam lineage -f semicolon rattus

10114(0): root;cellular organisms;Eukaryota;Opisthokonta;Metazoa;Eumetazoa;Bilateria;Deuterostomia;Chordata;Craniata <chordates>;Vertebrata <vertebrates>;Gnathostomata <vertebrates>;Teleostomi;Euteleostomi;Sarcopterygii;Dipnotetrapodomorpha;Tetrapoda;Amniota;Mammalia;Theria <mammals>;Eutheria;Boreoeutheria;Euarchontoglires;Glires;Rodentia;Myomorpha;Muroidea;Muridae;Murinae;Rattus [144]
```
Note that requesting a lineage including `--descendants` in semicolon form will result in the the output of a complete lineage for each child node of the target:
```
$ famdb.py -i ./dfam lineage -f semicolon -d rattus

10114(0): root;cellular organisms;Eukaryota;Opisthokonta;Metazoa;Eumetazoa;Bilateria;Deuterostomia;Chordata;Craniata <chordates>;Vertebrata <vertebrates>;Gnathostomata <vertebrates>;Teleostomi;Euteleostomi;Sarcopterygii;Dipnotetrapodomorpha;Tetrapoda;Amniota;Mammalia;Theria <mammals>;Eutheria;Boreoeutheria;Euarchontoglires;Glires;Rodentia;Myomorpha;Muroidea;Muridae;Murinae;Rattus [144]
10116(0): root;cellular organisms;Eukaryota;Opisthokonta;Metazoa;Eumetazoa;Bilateria;Deuterostomia;Chordata;Craniata <chordates>;Vertebrata <vertebrates>;Gnathostomata <vertebrates>;Teleostomi;Euteleostomi;Sarcopterygii;Dipnotetrapodomorpha;Tetrapoda;Amniota;Mammalia;Theria <mammals>;Eutheria;Boreoeutheria;Euarchontoglires;Glires;Rodentia;Myomorpha;Muroidea;Muridae;Murinae;Rattus;Rattus norvegicus [90]
10117(0): root;cellular organisms;Eukaryota;Opisthokonta;Metazoa;Eumetazoa;Bilateria;Deuterostomia;Chordata;Craniata <chordates>;Vertebrata <vertebrates>;Gnathostomata <vertebrates>;Teleostomi;Euteleostomi;Sarcopterygii;Dipnotetrapodomorpha;Tetrapoda;Amniota;Mammalia;Theria <mammals>;Eutheria;Boreoeutheria;Euarchontoglires;Glires;Rodentia;Myomorpha;Muroidea;Muridae;Murinae;Rattus;Rattus rattus [1120]

```

The `totals` format prints the number of ancestral and of lineage-specific repeats known for the given species.  
```
$ famdb.py -i ./dfam lineage -ad -f totals rattus

1134 entries in ancestors; 1151 lineage-specific entries; found in partitions: 0;
```

The `-c`/`--curated` or `-u`/`--uncurated` flags can be used with the `lineage` command, in any format.
```
$ famdb.py -i ./dfam lineage -adc -f totals rattus

1134 entries in ancestors; 31 lineage-specific entries; found in partitions: 0;

$ famdb.py -i ./dfam lineage -adc rattus

1 root(0) [9]
└─33208 Metazoa(0) [5]
  └─7742 Vertebrata <vertebrates>(0) [80]
    └─117571 Euteleostomi(0) [1]
      └─32523 Tetrapoda(0) [19]
        └─32524 Amniota(0) [102]
          └─40674 Mammalia(0) [67]
            └─32525 Theria <mammals>(0) [69]
              └─9347 Eutheria(0) [388]
                └─1437010 Boreoeutheria(0) [40]
                  └─314146 Euarchontoglires(0) [44]
                    └─314147 Glires(0) [3]
                      └─9989 Rodentia(0) [18]
                        └─1963758 Myomorpha(0) [17]
                          └─337687 Muroidea(0) [59]
                            └─10066 Muridae(0) [35]
                              └─39107 Murinae(0) [186]
                                └─10114 Rattus(0) [144]
                                  ├─10116 Rattus norvegicus(0) [90]
                                  └─10117 Rattus rattus(0) [0]


$ famdb.py -i ./dfam lineage -adu -f totals rattus

0 entries in ancestors; 1120 lineage-specific entries; found in partitions: 0;

$ famdb.py -i ./dfam lineage -adu rattus

1 root(0) [0]
└─33208 Metazoa(0) [0]
  └─7742 Vertebrata <vertebrates>(0) [0]
    └─117571 Euteleostomi(0) [0]
      └─32523 Tetrapoda(0) [0]
        └─32524 Amniota(0) [0]
          └─40674 Mammalia(0) [0]
            └─32525 Theria <mammals>(0) [0]
              └─9347 Eutheria(0) [0]
                └─1437010 Boreoeutheria(0) [0]
                  └─314146 Euarchontoglires(0) [0]
                    └─314147 Glires(0) [0]
                      └─9989 Rodentia(0) [0]
                        └─1963758 Myomorpha(0) [0]
                          └─337687 Muroidea(0) [0]
                            └─10066 Muridae(0) [0]
                              └─39107 Murinae(0) [0]
                                └─10114 Rattus(0) [0]
                                  ├─10116 Rattus norvegicus(0) [0]
                                  └─10117 Rattus rattus(0) [1120]
```
