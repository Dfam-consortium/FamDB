#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
    Usage: ./python-script.py [--help] --myarg1=foo --myarg2=bar

    This script partitions the Dfam database into taxonomy groups of equal file size. 
    It starts by assembling the subtree T of NCBI taxonomy (or retrieving a cached assembly).
    Tax ids and parent ids are queried from dfam_taxdb, then the parent ids and their 
    parent ids are queried from ncbi_taxdb_nodes until all parent ids are also present
    in the tax id list. The filesizes for each family related to each node are also retrieved.
    The tree is assembled and labeled with the total file size of all hmm blobs associated 
    with each node. Then each node is also labeled with the total file size of itself and all
    of it's children. The tree T is then pickled. 
    The node with the greatest total filesize less than S is identified, and it and all of it's
    children are labeled with a chunk id and their total weights are set to zero. Then all of
    thier parents have the weight of the chunk root subtracted from thier weights. This process
    is repeated until the total weight of T is less than S, and all remaining nodes are assigned 
    to chunk 0. 
    The chunks are then assembled into a tree F, where nodes have the attributes:
        T_root: The T node that is the root of the chunk subtree
        T_parent: The T node that is the parent of T_root
        bytes: The total file size in bytes of the nodes comprising the chunk
        nodes: A list of the nodes in the chunk
        children: A list of child F nodes
        F_parent: The parent F node of the chunk
    F is then saved to JSON or stdout.
    A newick representation of T is saved, as well as a metadata csv.

    Args:
        --help, -h        : Show this help message and exit
        --log-level, -l   : Control the logger level of the script
        --dfam_config, -c : Dfam Config file
        --version, -v     : Get Dfam Version
        --chunk_size, -S  : Maximum file size of the partitions in bytes (default 10,000,000,000)
        --rep_base, -r    : Save space for Repbase Data in the partitions

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
    parser.add_argument("-S", "--chunk_size", dest="chunk_size", default=10000000000)
    parser.add_argument("-r", "--rep_base", dest="rep_base", action="store_true")
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

    # ~ GENERATE T ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # check to see if tree has been cached
    T_file = f"{PREPPED_DIR}/T.pkl"
    if os.path.exists(T_file):
        LOGGER.info("Found Stashed T")
        with open(T_file, "rb") as phandle:
            T = pickle.load(phandle)
    else:
        LOGGER.info("Did not find Stashed Tree, Fetching Nodes")
        # Setup the database connections
        conf = dc.DfamConfig(args.dfam_config)
        dfamdb = create_engine(conf.getDBConnStrWPassFallback("Dfam"))
        dfamdb_sfactory = sessionmaker(dfamdb)
        session = dfamdb_sfactory()

        # query nodes from Dfam
        node_query = "SELECT dfam_taxdb.tax_id, parent_id FROM `ncbi_taxdb_nodes` JOIN dfam_taxdb ON dfam_taxdb.tax_id = ncbi_taxdb_nodes.tax_id"# ORDER BY dfam_taxdb.tax_id ASC"
        
        # if RepBase is included, add the taxa to the list
        if args.rep_base:
            rb_taxa_file = f"{PREPPED_DIR}/RMRB_spec_to_tax.json"
            if os.path.exists(rb_taxa_file):
                LOGGER.info("Found RepBase Taxa File")
                with open(rb_taxa_file, "rb") as spec_file:
                    spec_to_taxa = json.load(spec_file)
                node_query += f" UNION SELECT tax_id, parent_id from ncbi_taxdb_nodes WHERE tax_id IN ({','.join(str(node) for node in spec_to_taxa.values())})"
            else:
                LOGGER.error("RMRB_spec_to_tax.json Not Found\nRun embl_parser.py")
                exit()

        with session.bind.begin() as conn:
            tax_ids, parent_ids = zip(*conn.execute(node_query))
            tax_ids = list(tax_ids)
            parent_ids = list(parent_ids)

            # query parents of Dfam nodes until a connected tree can be built
            while True:
                missing_parents = []
                for parent in parent_ids:
                    if parent not in tax_ids:
                        missing_parents.append(parent)
                if not missing_parents:
                    break
                update_query = f"SELECT tax_id, parent_id FROM `ncbi_taxdb_nodes` WHERE tax_id IN ({','.join(str(node) for node in missing_parents)})"
                new_taxs, new_parents = zip(*conn.execute(update_query))
                new_taxs = list(new_taxs)
                new_parents = list(new_parents)
                tax_ids.extend(new_taxs)
                parent_ids.extend(new_parents)

        # query file sizes for each node
        # node_query = "SELECT family_clade.dfam_taxdb_tax_id, OCTET_LENGTH(hmm_model_data.hmm) FROM hmm_model_data JOIN family_clade ON hmm_model_data.family_id = family_clade.family_id"
        node_query = "SELECT family_clade.dfam_taxdb_tax_id, OCTET_LENGTH(hmm_model_data.hmm) + OCTET_LENGTH(family.consensus) FROM hmm_model_data JOIN family_clade ON hmm_model_data.family_id = family_clade.family_id JOIN family ON family_clade.family_id = family.id"
        with session.bind.begin() as conn:
            filesizes = conn.execute(node_query)

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
        
        # add sizes from RepBase 
        if args.rep_base:
            RB_file = f"{PREPPED_DIR}/RMRB.sizes"
            if os.path.exists(RB_file):
                LOGGER.info("Found RepBase Taxa Sizes")
                with open(RB_file, "rb") as size_file:
                    RB = json.load(size_file)
                for fam in RB:
                    tax_id = fam["tax_id"]
                    if tax_id in T:
                        T[tax_id]["filesize"] += fam["seq_size"]
                    else:
                        T[tax_id]["filesize"] = fam["seq_size"]
            else:
                LOGGER.error("RMRB.sizes Not Found\nRun embl_parser.py")
                exit()

        # assign children
        for n in T:
            parent = T[n]["parent"]
            if parent:
                T[parent]["children"].append(n)

        # root (node 1) is a child/parent of itself. Remove to allow recursion
        T[1]["children"].remove(1)
        T[1]["parent"] = None

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

        assign_total_weights(1)

        LOGGER.info("Stashing Tree")
        with open(T_file, "wb") as phandle:
            # pickle with protocol 4 since we require python 3.6.8 or later
            pickle.dump(T, phandle, protocol=4)

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

    LOGGER.info(f"Orig Tree Weight: {T[1]['tot_weight']}")
    S = args.chunk_size
    F = {}
    # ~ MAIN ASSIGNMENT LOOP ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    chunk_ctr = 1
    chunk_root, chunk_weight = 1, 0
    # split chunks off of T as long as remaining weight is greater than S
    while T[1]["tot_weight"] > S:
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
        chunk_root, chunk_weight = 1, 0
        chunk_ctr += 1

    # ~ CHUNK 0 ASSIGNMENT / CLEANUP ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # assign remaining T to chunk 0
    chunk_ctr = 0
    LOGGER.info(f"Chunk 0 Root:1, Weight {T[1]['tot_weight']}")
    F[0] = {"T_root": 1, "bytes": T[1]["tot_weight"], "nodes": [], "F_roots": []}
    label_chunk(1)
    subtract_chunk(1, T[1]["tot_weight"])

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
    with open(f"{PREPPED_DIR}/F.json", "w") as outfile:
        json.dump(F, outfile)

    # ~ NEWICK OUTPUT VISUALIZER ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    with open(f"{PREPPED_DIR}/T.csv", "w") as outfile:
        outfile.write("node, chunk\n" + "\n".join([f"{n},{T[n]['chunk']}" for n in T]))

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

    newick_str = newick(1) + ";"
    with open(f"{PREPPED_DIR}/T.newick", "w") as outfile:
        outfile.write(newick_str)


#
# Wrap script functionality in main() to avoid automatic execution
# when imported ( e.g. when help is called on file )
#
if __name__ == "__main__":
    main(*sys.argv)