#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
    This script can be used to check the data contained in FamDB files. 
    It performs the following tests:
        Open the file as an h5py file
        Load and display metadata including version info and expected counts
        Test for the existence of the datasets expected in FamDB files
        Attempt to use the FamDBRoot or FamDBLeaf classes to read the file
        Check for any interruptions in the file's change log.
    
    Note that this does require h5py and a FamDB installation to function.

    Usage: file_checker.py /input/path

    input    : A path to the file to check.

SEE ALSO:
    famdb.py
    Dfam: http://www.dfam.org

AUTHOR(S):
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
import os
import logging
import argparse
import h5py
import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from famdb_classes import FamDBLeaf, FamDBRoot
from famdb_globals import (
    FILE_DESCRIPTION,
    GROUP_FAMILIES,
    GROUP_LOOKUP_BYNAME,
    GROUP_NODES,
    GROUP_TAXANAMES,
    GROUP_OTHER_DATA,
    GROUP_REPEATPEPS,
    GROUP_FILE_HISTORY,
)

# List of expected file groups in FamDb files.
# True indicates that it should be in all files, False that it should only appear in a root file
file_groups = {
    GROUP_FAMILIES: True,
    GROUP_LOOKUP_BYNAME: False,
    GROUP_NODES: True,
    GROUP_TAXANAMES: False,
    GROUP_OTHER_DATA: True,
    f"{GROUP_OTHER_DATA}/{GROUP_REPEATPEPS}": False,
    f"{GROUP_OTHER_DATA}/{GROUP_FILE_HISTORY}": True,
}


def attempt(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            print(f"Function {func.__name__} Failed: {e}")
            exit(1)

    return wrapper


@attempt
def file_is_root(path):
    if "." not in path or "h5" not in path:
        raise Exception("File does not appear to be a partitioned FamDB H5 file")
    splits = path.split(".")
    return int(splits[-2]) == 0


@attempt
def get_group(file, group):
    thing = file.get(group)
    if thing:
        has_keys = callable(getattr(thing, "keys", False))
        if has_keys:
            keys = thing.keys()
            if group == GROUP_FAMILIES:
                return set(keys) <= {
                    "Aux",
                    "DF",
                    "DR",
                }  # all families should be sorted into one of these three bins
            if group == GROUP_LOOKUP_BYNAME:
                return len(keys) > 0  # names vary, just testing that there is more than one element
            if group == GROUP_NODES:
                return (
                    all(x.isdigit() for x in set(keys))
                )  # test that all elements are numbers
            if group == GROUP_TAXANAMES:
                return (
                    all(x.isdigit() for x in set(keys))
                )  # test that all elements are numbers 
            if group == GROUP_OTHER_DATA:
                return (
                    len(keys) == 2 or len(keys) == 1
                )  # should be exactly two elements for root, 1 for leaf
            if group == f"{GROUP_OTHER_DATA}/{GROUP_FILE_HISTORY}":
                for elem in keys:
                    try:
                        datetime.datetime.strptime(
                            elem, "%Y-%m-%d %H:%M:%S.%f"
                        )  # test that all elements are datetimes
                    except ValueError:
                        return False
                return True
        else:
            if group == f"{GROUP_OTHER_DATA}/{GROUP_REPEATPEPS}":
                return True # if this exists, it's just a dataset

    return False


@attempt
def get_famdb_class(is_root, path):
    if is_root:
        return FamDBRoot(path, "r")
    else:
        return FamDBLeaf(path, "r")


def main():
    logging.basicConfig()

    parser = argparse.ArgumentParser(
        description=FILE_DESCRIPTION,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("input")
    args = parser.parse_args()

    is_root_file = file_is_root(args.input)

    try:
        print(f"Testing that {args.input} can be opened as H5 file...")
        with h5py.File(args.input, "r") as file:
            print(
                "  Metatadata Retrieved:\n"
                f"    FamDB Version: {file.attrs['famdb_version'] if file.attrs.get('famdb_version') else file.attrs['version']}\n"
                f"    FamDB Generator Version: {file.attrs['generator']}\n"
                f"    File Created: {file.attrs['created']}\n"
                f"    Name: {file.attrs['db_name']}\n"
                f"    Dfam Version: {file.attrs['db_version']}\n"
                f"    Consensi Count: {file.attrs['count_consensus']}\n"
                f"    HMM Count: {file.attrs['count_hmm']}"
            )
            all_expected_groups = True
            for group in file_groups:
                if (
                    is_root_file or file_groups[group]
                ):  # check all groups for root files, but only selected ones for leaf files
                    print(f"  Testing Group: {group}")
                    if not get_group(file, group):
                        print(f"\t {group} Not found, or not as expected")
                        all_expected_groups = False
            if all_expected_groups:
                print("  All Expected Groups Found")
           

    except Exception as e:
        print(f"{args.input} Could not be Opened as an H5 File: {e}")
        exit(1)

    try:
        print(
            f"Testing that {args.input} can be opened with the {'FamDBRoot' if is_root_file else 'FamDBLeaf'} class..."
        )
        with get_famdb_class(is_root_file, args.input) as file:
            if file.interrupt_check():
                print(
                    f"{args.input} Was Interrupted During Writing. Corruption Possible"
                )
            else:
                print(f"  No Interruption Detected")

    except Exception as e:
        print(f"{args.input} Could Not Be Opened As An H5 File: {e}")
        exit(1)


if __name__ == "__main__":
    main()
