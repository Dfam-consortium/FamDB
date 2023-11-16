#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
    Set the version/date of a pre-built FamDB database

    Usage: set_ver_date.py [-h] [-l LOG_LEVEL]
               [--db-version 3.2]
               [--db-date YYYY-MM-DD]
               famdb_database_dir


    --db-version    : Set the database version explicitly, overriding the version in --from-db if present.
    --db-date       : Set the database date explicitly, overriding the date in --from-db if present.
                      If not given, the current date will be used.

SEE ALSO:
    famdb.py
    Dfam: http://www.dfam.org

AUTHOR(S):
    Robert Hubley <rhubley@systemsbiology.org>

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
import time
import h5py

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from famdb_globals import DESCRIPTION, COPYRIGHT_TEXT


LOGGER = logging.getLogger(__name__)


def main():
    """Parses command-line arguments and runs the import."""

    logging.basicConfig()

    parser = argparse.ArgumentParser()
    parser.add_argument("-l", "--log-level", default="INFO")
    parser.add_argument("--db-version")
    parser.add_argument("--db-date")
    parser.add_argument("db_dir")

    args = parser.parse_args()
    logging.getLogger().setLevel(getattr(logging, args.log_level.upper()))

    new_creation_time = str(datetime.datetime.now())

    open_mode = "r+"
    if not args.db_version and not args.db_date:
        open_mode = "r"

    for filename in os.listdir(args.db_dir):
        matches = re.match(r"\S+\.(\d+)\.h5", filename)
        if matches:
            with h5py.File(os.path.join(args.db_dir,filename), mode=open_mode) as h5f:
                print(filename + ":")
                db_version = h5f.attrs['db_version']
                db_date = h5f.attrs['db_date']
                db_copyright = h5f.attrs['db_copyright']
                meta_created = h5f.attrs['created']

                print("  current: dfam version: {}".format(db_version))

                if args.db_version:
                    db_version = args.db_version
                    h5f.attrs['db_version'] = db_version
                    print("    ** new: db_info - dfam version: {}".format(db_version))

                print("  current: db_meta - famdb creation date: {}".format(meta_created))
                print("  current: db_info - dfam creation date: {}".format(db_date))
                print("  current: copyright: {}".format(db_copyright))
                if args.db_date:
                    db_date = args.db_date
                    year_match = re.match(r'^(\d{4})-\d{2}-\d{2}$', db_date)
                    if year_match:
                        db_year = year_match.group(1)
                    else:
                        raise Exception("Date should be in YYYY-MM-DD format, got: " + db_date)

                    copyright_text = COPYRIGHT_TEXT % (
                        db_year,
                        db_version,
                        db_date,
                      )
                    h5f.attrs['db_copyright'] = copyright_text
                    h5f.attrs['db_date'] = db_date
                    h5f.attrs['created'] = new_creation_time
                    print("    ** new: db_meta - famdb creation date: {}".format(new_creation_time))
                    print("    ** new: db_info - dfam creation date: {}".format(db_date))
                    print("    ** new: copyright: {}".format(copyright_text))


if __name__ == "__main__":
    main()
