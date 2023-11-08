#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
    Usage: ./python-script.py [--help] --myarg1=foo --myarg2=bar

    This script counts the number of TE families in Dfam by group. It collects the child nodes
    of each of the listed taxonomy nodes, then queries the count of families belonging to those nodes.
    The included groups are:
        Mammalia (40674)
        Birds (8782)
        Reptiles (1294634, 8504, 8459)
        Amphibians (8292)
        Fish (7898, 7777, 118072, 7878, 117569, 117565)
        Echinoderms (7586)
        Protosomes (33317)
        Fungi (4751)
        Plants (33090)
        Other

    Args:
        --help, -h        : Show this help message and exit
        --log-level, -l   : Control the logger level of the script
        --dfam_config, -c : Dfam Config file
        --version, -v     : Get Dfam Version

SEE ALSO: related_script.py
          Dfam: http://www.dfam.org

AUTHOR(S):
    Anthony Gray agray@systemsbiology.org

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
# Module imports
import argparse
import logging
import os
import sys
import json
import uuid

# SQL Alchemy
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# TODO rm
tempwork = "/Dfam-umbrella"

import dfam_35 as dfam

# Import our Libs
sys.path.append(os.path.join(os.path.dirname(__file__), f"..{tempwork}/Lib"))
import DfamConfig as dc
import DfamVersion as dfVersion

LOGGER = logging.getLogger(__name__)
PREPPED_DIR = "partitions"

def _usage():
    """Print out docstring as program usage"""
    # Call to help/pydoc with scriptname ( sans path and file extension )
    help(os.path.splitext(os.path.basename(__file__))[0])
    sys.exit(0)

#
# main subroutine ( protected from import execution )
#
def main(*args):
    """Parse arguments and run"""

    logging.basicConfig(stream=sys.stdout, format="%(levelname)s: %(message)s")

    class _CustomUsageAction(argparse.Action):
        def __init__(
            self, option_strings, dest, default=False, required=False, help=None
        ):
            super(_CustomUsageAction, self).__init__(
                option_strings=option_strings,
                dest=dest,
                nargs=0,
                const=True,
                default=default,
                required=required,
                help=help,
            )

        def __call__(self, parser, args, values, option_string=None):
            _usage()

    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("-h", "--help", action=_CustomUsageAction)
    parser.add_argument("-l", "--log-level", default="INFO")
    parser.add_argument("-c", "--dfam_config", dest="dfam_config")
    parser.add_argument("-v", "--version", dest="get_version", action="store_true")
    args = parser.parse_args()

    logging.getLogger().setLevel(getattr(logging, args.log_level.upper()))

    #
    # Require Dfam Configuration
    #   Search order: --dfam_config <path>, environment DFAM_CONF,
    #                 and finally "../Conf/dfam.conf"
    #
    df_ver = dfVersion.DfamVersion()

    if args.get_version:
        LOGGER.info(df_ver.version_string)
        exit(0)

    # Setup the database connections
    conf = dc.DfamConfig(args.dfam_config)
    dfamdb = create_engine(conf.getDBConnStrWPassFallback("Dfam"))
    dfamdb_sfactory = sessionmaker(dfamdb)
    session = dfamdb_sfactory()

    version_info = session.query(dfam.DbVersion).one()
    db_version = version_info.dfam_version
    db_date = version_info.dfam_release_date.strftime("%Y-%m-%d")

    target_groups = {
        'Mammalia': [40674],
        'Birds': [8782],
        'Reptiles': [1294634, 8504, 8459],
        'Amphibians': [8292],
        'Fish': [7898, 7777, 118072, 7878, 117569, 117565],
        'Echinoderms': [7586],
        'Protosomes': [33317],
        'Fungi': [4751],
        'Plants': [33090],
    }

    group_sizes = {
        'Mammalia': 0,
        'Birds': 0,
        'Reptiles': 0,
        'Amphibians': 0,
        'Fish': 0,
        'Plants': 0,
        'Echinoderms': 0,
        'Protosomes': 0,
        'Fungi': 0,
    }

    def get_nodes(nodes):
        node_query = f"SELECT tax_id FROM `ncbi_taxdb_nodes` WHERE parent_id IN ({','.join(str(node) for node in nodes)})"
        with session.bind.begin() as conn:
            tax_ids = conn.execute(node_query)
            tax_ids = [id[0] for id in tax_ids]
        if tax_ids:
            tax_ids += get_nodes(tax_ids)
            return tax_ids
        else:
            return []

    def count_families(nodes):
        node_query = f"SELECT COUNT(family_id) FROM `family_clade` WHERE dfam_taxdb_tax_id IN ({','.join(str(node) for node in nodes)})"
        with session.bind.begin() as conn:
            count = conn.execute(node_query).fetchone()
        return count[0]

    for group in target_groups:
        target_groups[group] += get_nodes(target_groups[group])
        group_sizes[group] = count_families(target_groups[group])

    with session.bind.begin() as conn:
        count = conn.execute("SELECT COUNT(family_id) FROM `family_clade`").fetchone()
        group_sizes['Other'] = count[0]
    
    for group in group_sizes:
        if group != 'Other':
            group_sizes['Other'] -= group_sizes[group]

    out = {
        "meta": {
            "partition_id": str(uuid.uuid4()),
            "db_version": db_version,
            "db_date": db_date,
        },
        "group_sizes": group_sizes
    }
    with open(f"./group_sizes.json", "w") as outfile:
        json.dump(out, outfile)

#
# Wrap script functionality in main() to avoid automatic execution
# when imported ( e.g. when help is called on file )
#
if __name__ == "__main__":
    main(*sys.argv)
