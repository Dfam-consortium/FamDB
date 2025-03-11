# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## 1.0 - 2023-11-18
### Added
- The lineage function now accepts --curated, and --uncurated flags to
  filter lineage annotated counts based on the family curation status.
### Changed
- Breaking change to HDF5 schema (now v1.0).  FamDB is now a database
  capable of being partitioned.  A single root partition is required,
  however many additional leaf partitions may also be present.
- The commands available to the user have not changed, but instead of passing 
  the name of the `.h5` file to `famdb.py` with `-i`, the files must be in a 
  separate directory. The name of that directory is passed to `famdb.py` with 
  `-i` instead of the file names. More installation and use details are found 
  in `README.md`.
- The structure of the files have also changed. More technical details can be
  found in `README-dev.md`.

## 0.4.3 - 2023-01-09
### Added
- Most subcommands will now accept multiple arguments for a species name and
  treat it as a single space-separated string instead of raising an error. For
  instance, `famdb.py names homo sapiens` now works exactly the same as
  `famdb.py names 'homo sapiens'`
### Changed
- Major change to HDF5 schema (now v0.5) fixes performance issues with scaling
  to >>500k families.  HDF5 exhibits an increasing insertion time-cost for entries
  (datasets or links) within a group.  In our original schema families were stored
  in a single group.  In v0.5 we now bin families by two character prefix bins for
  Dfam and Auxiliary families.  Currently 0.4.3 is not backwards compatible and
  cannot read v0.4 formated files.
- `export_dfam.py` has been refactored and extended . It subsumes the previous
  functionality of `convert_hmm.py`, which has been removed.
### Fixed
- Fixed numerous bugs with HMM-only libraries produced by `convert_hmm.py`/`export_dfam.py`

## 0.4.2 - 2021-03-30
### Fixed
- famdb now correctly recognizes the "Refineable" annotation for RepeatMasker
  when reading EMBL files (e.g. 'famdb.py append' and 'export_dfam.py')

## 0.4.1 - 2021-03-08
### Added
- Added options to the `families` command: `--add-reverse-complement`,
  `--include-class-in-name`, `--uncurated`
- If no file is specified, `famdb.py` will operate on the file
  `Libraries/RepeatMaskerLib.h5` if it exists
- The `--class` option for the `families` command now accepts a subtype, for
  example `DNA/CMC` instead of only `DNA`
### Fixed
- Disable HDF5's file locking when reading files, since it's unnecessary in
  that context and unreliable on some filesystems
- Piping `famdb.py` to utilities that stop reading output early, such as
  `head` or `less`, no longer produces a `BrokenPipeError`

## 0.4 - 2020-09-02
- Initial release
- Included with RepeatMasker 4.1.1
