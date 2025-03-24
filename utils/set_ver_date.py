#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
    Set the version/date of a pre-built FamDB database

    Usage: set_ver_date.py [-h] [-l LOG_LEVEL]
               [--db-version 3.2]
               [--db-date YYYY-MM-DD]
               [--db-name Test_name]
               [--db-description  'New Description']
               [--file-info dump/load]
               [-t d]
               famdb_database_dir


    --db-version        : Set the database version explicitly, overriding the version in --from-db if present.
    --db-date           : Set the database date explicitly, overriding the date in --from-db if present.
                          If not given, the current date will be used.
    --db-name           : Set the database name.
    --db-description    : Set the database description.
    --file-info         : This argument takes two options, either 'dump' or 'load'. Dump outputs the file info 
                          JSON string to a file, and load loads that file back into the FamDB files. The file 
                          can be edited by hand.
    --input-type, -t    : Input type can be 'd' or 'directory' for editing whole FamDB installations, or 'f' 
                          or 'file' to modify individual files.
    input               : This path to the file or directory to be edited.

SEE ALSO:
    famdb.py
    Dfam: http://www.dfam.org

AUTHOR(S):
    Robert Hubley <rhubley@systemsbiology.org>
    Anthony Gray <agray@systemsbiology.org>

LICENSE:
    This code may be used in accordance with the Creative Commons
    Zero ("CC0") public domain dedication:
    https://creativecommons.org/publicdomain/zero/1.0/

DISCLAIMER:
    This software is provided ``AS IS'' and any express or implied
    warranties, including, but not limited to, the implied warranties of
    merchantability and fitness for a particular purpose, are disclaimed.
    In no event shall the authors or the Dfam consortium members be
    liable for any direct, indirect, incidental, special, exemplary, or
    consequential damages (including, but not limited to, procurement of
    substitute goods or services; loss of use, data, or profits; or
    business interruption) however caused and on any theory of liability,
    whether in contract, strict liability, or tort (including negligence
    or otherwise) arising in any way out of the use of this software, even
    if advised of the possibility of such damage.
"""

import sys
import argparse
import datetime
import logging
import os
import re
import h5py
import json

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from famdb_globals import (
    META_DB_DESCRIPTION,
    META_DB_NAME,
    META_DB_COPYRIGHT,
    META_FILE_INFO,
    META_DB_VERSION,
    META_DB_DATE,
    META_CREATED,
    COPYRIGHT_TEXT,
)

LOGGER = logging.getLogger(__name__)


def update_file(file_path, open_mode, new_creation_time, args):
    with h5py.File(file_path, mode=open_mode) as h5f:
        print(file_path + ":")
        db_version = h5f.attrs[META_DB_VERSION]
        db_date = h5f.attrs[META_DB_DATE]
        db_copyright = h5f.attrs[META_DB_COPYRIGHT]
        meta_created = h5f.attrs[META_CREATED]
        db_name = h5f.attrs[META_DB_NAME]
        db_description = h5f.attrs[META_DB_DESCRIPTION]
        print(f"  current: dfam version: {db_version}")
        print(f"  current: meta_created - famdb creation date: {meta_created}")
        print(f"  current: db_date - dfam creation date: {db_date}")
        print(f"  current: db_name - dfam name: {db_name}")
        print(f"  current: db_desc - dfam description: {db_description}")
        print(f"  current: copyright: {db_copyright}")

        if args.db_version:
            db_version = args.db_version
            h5f.attrs[META_DB_VERSION] = db_version
            print(f"    ** new: db_version - dfam version: {db_version}")

        if args.db_name:
            db_name = args.db_name
            h5f.attrs[META_DB_NAME] = db_name
            print(f"    ** new: db_name - dfam db_name: {db_name}")

        if args.db_description:
            db_description = args.db_description
            h5f.attrs[META_DB_DESCRIPTION] = db_description
            print(f"    ** new: db_desc - dfam description: {db_description}")

        dump_base = '_file_info.json'
        dump_name = f"{db_name}{dump_base}"
        if args.file_info and args.file_info == 'dump':
            file_info = h5f.attrs[META_FILE_INFO]
            info_obj = json.loads(file_info)
            with open(dump_name, 'w') as outfile:
                json.dump(info_obj, outfile, indent=4)
            print(f"File Info Dumped To {dump_name}")
            
        if args.db_date:
            db_date = args.db_date
            year_match = re.match(r"^(\d{4})-\d{2}-\d{2}$", db_date)
            if year_match:
                db_year = year_match.group(1)
                copyright_text = COPYRIGHT_TEXT % (
                db_year,
                db_version,
                db_date,
                )
                h5f.attrs[META_DB_COPYRIGHT] = copyright_text
                h5f.attrs[META_DB_DATE] = db_date
                h5f.attrs[META_CREATED] = new_creation_time
                print(f"    ** new: db_meta - famdb creation date: {new_creation_time}")
                print(f"    ** new: db_date - dfam creation date: {db_date}")
                print(f"    ** new: copyright: {copyright_text}")
            else:
                raise Exception("Date should be in YYYY-MM-DD format, got: " + db_date)
        
        if args.file_info and args.file_info == 'load':
            try:
                with open(dump_name, 'r') as outfile:
                    new_info = json.load(outfile)
                h5f.attrs[META_FILE_INFO] = json.dumps(new_info)
                print(f"File Info Loaded From {dump_name}")  
            except:                     
                raise Exception("File Info Not In JSON Format")

def main():
    """Parses command-line arguments and runs the import."""

    logging.basicConfig()

    parser = argparse.ArgumentParser()
    parser.add_argument("-l", "--log-level", default="INFO")
    parser.add_argument("--db-version")
    parser.add_argument("--db-date")
    parser.add_argument("--db-name")
    parser.add_argument("--db-description")
    parser.add_argument("--file-info", choices=('load', 'dump'))
    parser.add_argument("-t", "--input-type", choices=("f", "file", "d", "directory"))
    parser.add_argument("input")

    args = parser.parse_args()
    logging.getLogger().setLevel(getattr(logging, args.log_level.upper()))

    new_creation_time = str(datetime.datetime.now())

    open_mode = "r+"
    input = args.input
    if args.input_type == "f" or args.input_type == "file":
        matches = re.match(r"\S+\.(\d+)\.h5", filename)
        if matches:
            update_file(input, open_mode, new_creation_time, args)

    elif args.input_type == "d" or args.input_type == "directory":
        for filename in os.listdir(input):
            matches = re.match(r"\S+\.(\d+)\.h5", filename)
            if matches:
                file_path = os.path.join(input, filename)
                update_file(file_path, open_mode, new_creation_time, args)

    else:
        print("Please Specify If The Input Is A Single File (-f) Or A Directory (-d)")


if __name__ == "__main__":
    main()
