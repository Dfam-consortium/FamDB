### names
```
usage: famdb.py names [-h] [-f <format>] term [term ...]

List the names and taxonomy identifiers of a clade.

positional arguments:
  term                  search term. Can be an NCBI taxonomy identifier or
                        part of a scientific or common name

optional arguments:
  -h, --help            show this help message and exit
  -f <format>, --format <format>
                        choose output format. The default is 'pretty'. 'json'
                        is more appropriate for scripts.
```
Searches the taxonomy database for species names and prints all known names for
any matches. The output is human-readable ("pretty") by default but can also be
in JSON format. The JSON format is intended for parsing by scripts; the pretty
format is too unstructured to parse reliably.

`term` can be a taxonomy identifier number or part of a species/clade name.
In this example the FamDB files are stored in a directory called 'dfam' in 
the current working directory.  RepeatMasker looks for them in its "Library/famdb"
directory by default.

Exact matches are distinguished from non-exact matches.  

#### Example:
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
