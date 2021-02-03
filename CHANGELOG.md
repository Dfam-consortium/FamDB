# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## Unreleased
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
