#!/usr/bin/python3
# -*- coding: utf-8 -*-

# Module imports
import argparse
import logging
import pickle
import os
import sys
import json

# SQL Alchemy
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# TODO rm
tempwork = "/Dfam-umbrella"

# Import our Libs
sys.path.append(os.path.join(os.path.dirname(__file__), f"..{tempwork}/Lib"))
import DfamConfig as dc
import DfamVersion as dfVersion

LOGGER = logging.getLogger(__name__)
PREPPED_DIR = "partitions"
T_file = f"{PREPPED_DIR}/T_test.pkl"
F_file = f"{PREPPED_DIR}/F_mam.json"
root_node = 33416

def _usage():
    """Print out docstring as program usage"""
    # Call to help/pydoc with scriptname ( sans path and file extension )
    help(os.path.splitext(os.path.basename(__file__))[0])
    sys.exit(0)

def generate_T(args, session):
    # query nodes from Dfam
    node_query = f"SELECT tax_id, parent_id FROM `ncbi_taxdb_nodes` WHERE tax_id = {root_node}" 

    with session.bind.begin() as conn:
        tax_ids, parent_ids = zip(*conn.execute(node_query))
        tax_ids = list(tax_ids)
        parent_ids = list(parent_ids)
        # query parents of Dfam nodes until a connected tree can be built
        while True:
            possible_parent = []
            for node in tax_ids:
                if node not in parent_ids:
                    possible_parent.append(node)
            update_query = f"SELECT tax_id, parent_id FROM `ncbi_taxdb_nodes` WHERE parent_id IN ({','.join(str(node) for node in possible_parent)})"
            res = [r for r in conn.execute(update_query)]
            LOGGER.info(len(res))
            if not res:
                break
            new_taxas = []
            new_parents = []
            for node in res:
                new_taxas.append(node[0])
                new_parents.append(node[1])
            tax_ids.extend(new_taxas)
            parent_ids.extend(new_parents)

        # query file sizes for each node
        node_query = f"SELECT family_clade.dfam_taxdb_tax_id, OCTET_LENGTH(hmm_model_data.hmm) + OCTET_LENGTH(family.consensus) FROM hmm_model_data JOIN family_clade ON hmm_model_data.family_id = family_clade.family_id JOIN family ON family_clade.family_id = family.id WHERE family_clade.dfam_taxdb_tax_id IN ({','.join(str(node) for node in set(tax_ids))})"
        filesizes = conn.execute(node_query)

    tax_ids += [root_node]
    parent_ids += [None]
    LOGGER.info("Building Tree")
    # assemble tree from node info
    T = {
        z[0]: {
            "parent": z[1],
            "children": [],
            "filesize": 0,
            "tot_weight": 0,
            "chunk": None,
        }
        for z in zip(tax_ids, parent_ids)
    }

    # assign filesizes
    for size in filesizes:
        T[size[0]]["filesize"] += size[1]

    # assign children
    for n in T:
        parent = T[n]["parent"]
        if parent:
            T[parent]["children"].append(n)

    # Assign tot_weight for each node as the sum of its filesize and the filesizes of all of it's child nodes
    def assign_total_weights(n):
        n_size = T[n]["filesize"]
        children = T[n]["children"]
        if not children:
            T[n]["tot_weight"] = n_size
            return n_size
        else:
            for child in children:
                n_size += assign_total_weights(child)
            T[n]["tot_weight"] = n_size
            return n_size

    assign_total_weights(root_node)

    LOGGER.info("Stashing Tree")
    with open(T_file, "wb") as phandle:
        # pickle with protocol 4 since we require python 3.6.8 or later
        pickle.dump(T, phandle, protocol=4)
    return T


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
    parser.add_argument("-S", "--chunk_size", dest="chunk_size", default=100000000)
    parser.add_argument("-r", "--rep_base", dest="rep_base")
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

    # ~ GENERATE T ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # check to see if tree has been cached
    if os.path.exists(T_file):
        LOGGER.info("Found Stashed T")
        with open(T_file, "rb") as phandle:
            T = pickle.load(phandle)
    else:
        LOGGER.info("Did not find Stashed Tree, Fetching Nodes")
        T = generate_T(args, session)

    # ~ CHUNK ASSIGNMENT ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def label_chunk(n):
        # assign chunk label if unassigned
        if not T[n]["chunk"]:
            T[n]["chunk"] = chunk_ctr
        # unweight node
        T[n]["tot_weight"] = 0
        # recursive call to children
        children = T[n]["children"]
        if children:
            for child in children:
                label_chunk(child)

    def subtract_chunk(n, sub_weight):
        # subtract chunk weight from all parents of chunk
        parent = T[n]["parent"]
        if parent:
            T[parent]["tot_weight"] -= sub_weight
            subtract_chunk(parent, sub_weight)

    LOGGER.info(f"Orig Tree Weight: {T[root_node]['tot_weight']}")
    S = args.chunk_size
    F = {}
    # ~ MAIN ASSIGNMENT LOOP ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    chunk_ctr = 1
    chunk_root, chunk_weight = 1, 0
    # split chunks off of T as long as remaining weight is greater than S
    while T[root_node]["tot_weight"] > S:
        # find largest node less than S
        for n in T:
            size = T[n]["tot_weight"]
            if size > 0 and size < S and size > chunk_weight:
                chunk_root = n
                chunk_weight = size

        # modify T with labels
        LOGGER.info(f"Chunk {chunk_ctr} Root:{chunk_root}, Weight {chunk_weight}")
        label_chunk(chunk_root)
        subtract_chunk(chunk_root, chunk_weight)

        # update F with chunk information
        F[chunk_ctr] = {
            "T_root": chunk_root,
            "bytes": chunk_weight,
            "nodes": [],
            "F_roots": [],
        }

        # reset loop and increment chunk counter
        chunk_root, chunk_weight = root_node, 0
        chunk_ctr += 1

    # ~ CHUNK 0 ASSIGNMENT / CLEANUP ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # assign remaining T to chunk 0
    chunk_ctr = 0
    LOGGER.info(f"Chunk 0 Root: {root_node}, Weight {T[root_node]['tot_weight']}")
    F[0] = {"T_root": root_node, "bytes": T[root_node]["tot_weight"], "nodes": [], "F_roots": []}
    label_chunk(root_node)
    subtract_chunk(root_node, T[root_node]["tot_weight"])

    # trace paths from chunk roots to root of T to ensure all chunks have parent chunk 0
    def trace_root_path(i):
        parent = T[i]["parent"]
        if parent:
            T[parent]["chunk"] = 0
            trace_root_path(parent)

    for n in F:
        trace_root_path(F[n]["T_root"])

    # ~ MAP T nodes to F chunks ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # fill nodes in F
    for n in T:
        node_chunk = T[n]["chunk"]
        F[node_chunk]["nodes"].append(n)

    # save chunk roots after path retrace
    for chunk in F:
        if chunk != 0:
            for n in F[chunk]["nodes"]:
                # check each node in chunk to see if it is a root
                T_parent = T[n]["parent"]
                # chunk roots will have parents in chunk 0
                if T[T_parent]["chunk"] == 0:
                    F[chunk]["F_roots"].append(n)

    LOGGER.info("")
    LOGGER.info("F nodes after root tracing:")
    for n in F:
        LOGGER.info(
            f"Chunk: {n}, roots {F[n]['F_roots']}, size: {sum([T[i]['filesize'] for i in F[n]['nodes']])}"
        )

    # ~ OUTPUTS ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # save F
    with open(F_file, "w") as outfile:
        json.dump(F, outfile)


    # ~ NEWICK OUTPUT VISUALIZER ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    with open(f"{PREPPED_DIR}/T_test.csv", "w") as outfile:
        outfile.write("node, chunk, filesize\n" + "\n".join([f"{n},{T[n]['chunk']},{T[n]['filesize']}" for n in T]))

    def newick(i):
        n_str = ""
        children = T[i]["children"]
        if not children:
            return f"{i}"
        for child in children:
            n_str += f"{newick(child)},"
        if n_str[-1] == ",":
            n_str = n_str[:-1]
        return f"({n_str}){i}"

    newick_str = newick(root_node) + ";"
    with open(f"{PREPPED_DIR}/T_test.newick", "w") as outfile:
        outfile.write(newick_str)

#
# Wrap script functionality in main() to avoid automatic execution
# when imported ( e.g. when help is called on file )
#
if __name__ == "__main__":
    main(*sys.argv)
