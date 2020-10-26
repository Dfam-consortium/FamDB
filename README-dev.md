# FamDB README for Developers

## Creating famdb files

A limited number of import and export formats are available at this time.

### HMM

`convert_hmm.py import` and `convert_hmm.py dump` convert from and to HMM format, respectively.

### Dfam Releases

`export_dfam.py` is used to build the famdb format for Dfam releases. It
requires a mysql connection to a Dfam database corresponding to a frozen
release.

```
$ /usr/bin/time ./export_dfam.py mysql://user:pass@host/database --extra-taxa-file extra_taxa.txt --extra-embl-file Supplemental.embl Dfam_curatedonly.h5
$ /usr/bin/time ./export_dfam.py mysql://user:pass@host/database --extra-taxa-file extra_taxa.txt --extra-embl-file Supplemental.embl -r Dfam.h5
```

## Unit Tests

Unit tests are written with Python's `unittest` package, and the test modules
are named in a way that is discoverable by `unittest` automatically:

```
$ python3 -m unittest
```
