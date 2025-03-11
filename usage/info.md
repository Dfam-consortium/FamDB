### info
```
usage: famdb.py info [-h] [--history]

List general information about the file.

optional arguments:
  -h, --help  show this help message and exit
  --history   List the file changelog in addition to general information
```
Prints general information and statistics about the database, such as title,
version, date, and count of consensus sequences and HMMs in the database.

Information about each partition will also be shown, including the partition number, the names of the included taxa, and the filenames and individual counts if the file is present.

The `--history` argument will also display the changelog for each file present.