## append
```
usage: famdb.py append [-h] [--name NAME] [--description DESCRIPTION] infile

positional arguments:
  infile                the name of the input file to be appended
  exclusion_file        the name of the file listing family names to be excluded

optional arguments:
  -h, --help            show this help message and exit
  --name NAME           new name for the database (replaces the existing name)
  --description DESCRIPTION
                        additional database description (added to the existing
                        description)
```

The append command can be used to add families from an EMBL file to the FamDB files. 
The families must map to a clade that is already contained in the FamDB files.
The command should also include a file listing names that occur in both Dfam and the appending file. These names will be excluded from the append to avoid duplicate information. An exclusion file for RepBase will be provided with the other FamDB file downloads.
If no names are to be excluded, an empty file can be used.

The `names` command can be used to determine which clades are available under which names.
The `--name` and `--description` arguments are available to modify so that the `info` command can reflect that the files have been modified.

**It is strongly reccomended that the FamDB files are backed up before modification.**

**Appending families can take a long time, and if the process is interrupted, the files will be corrupted and unusable.**

Example: append a file to an existing installation
```
nohup python3 ~/projects/Dfam-umbrella/FamDB/famdb.py -i ./dfam_export/ append ~/scratch/RepBase/Additional.embl rebase_dups.names --description 'Dfam X.Y with Additional families added'
```