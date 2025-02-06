"""
Fakes, stubs, etc. for use in testing FamDB
"""

from copy import deepcopy
from famdb_classes import FamDBLeaf, FamDBRoot
from famdb_helper_classes import TaxNode, Family
from famdb_globals import FAMDB_VERSION, DESCRIPTION

"""
        1
      /   \\
 (0) 2     3
--------------
(1)/ |\\ (2)
  4	 | *5
 /   |  \\
6    |    7
"""

TAX_NAMES = {
    1: "root",
    2: "Order",
    3: "Other Order",
    4: "Genus",
    5: "Other Genus",
    6: "Species",
    7: "Other Species",
}
COMMON_NAMES = {
    1: "Root Dummy 1",
    2: "Root Dummy 2",
    3: "Root Dummy 3",
    4: "Leaf Dummy 4",
    5: "Leaf Dummy 5",
    6: "Leaf Dummy 6",
    7: "Leaf Dummy 7",
}
# 0 - root, 1 - search, 2 - other
NODES = {0: [1, 2, 3], 1: [4, 6], 2: [5, 7]}

FILE_INFO = {
    "meta": {"partition_id": "uuidXX", "db_version": "V1", "db_date": "2020-07-15"},
    "file_map": {
        "0": {
            "T_root": 1,
            "filename": "unittest.0.h5",
            "F_roots": [],
            "T_root_name": "Root Node",
            "F_roots_names": [],
        },
        "1": {
            "T_root": 4,
            "filename": "unittest.1.h5",
            "F_roots": [4],
            "T_root_name": "Search Node",
            "F_roots_names": [],
        },
        "2": {
            "T_root": 5,
            "filename": "unittest.2.h5",
            "F_roots": [5],
            "T_root_name": "Other Node",
            "F_roots_names": ["Other Node"],
        },
    },
}

DB_INFO = ("Test Dfam", "V1", "2020-07-15", "<copyright header>")
FAKE_REPPEPS = "./tests/rep_pep_test.lib"


def build_taxa(nodes):
    for node in nodes.values():
        if node.tax_id != 1:
            node.parent_node = nodes[node.parent_id]
            node.parent_node.children += [node]
        node.names += [["scientific name", TAX_NAMES[node.tax_id]]]
        node.names += [["common name", COMMON_NAMES[node.tax_id]]]
    return nodes


# convenience function to generate a test family
def make_family(acc, clades, consensus, model):
    fam = Family()
    fam.accession = acc
    fam.name = "Test family " + acc
    fam.version = 1
    fam.clades = clades
    fam.consensus = consensus
    fam.model = model

    return fam


def write_test_metadata(db):
    # Override setting of format metadata for testing
    db.file.attrs["famdb_version"] = FAMDB_VERSION
    db.file.attrs["created"] = "<creation date>"
    db.file.attrs["db_description"] = DESCRIPTION


def init_db_file(filename):
    FAMILIES = [
        make_family("TEST0001", [1], "ACGT", "<model1>"),
        make_family("TEST0002", [2, 3], None, "<model2>"),
        make_family("TEST0003", [3], "GGTC", "<model3>"),
        make_family("TEST0004", [4], "CCCCTTTT", None),
        make_family("DR000000001", [7], "GCATATCG", None),
        make_family("DR_Repeat1", [6], "CGACTAT", None),
    ]
    families = FAMILIES

    families[1].name = None
    families[2].search_stages = "30,40"
    families[3].buffer_stages = "10[1-2],10[5-8],20"
    families[3].search_stages = "35"
    families[3].repeat_type = "SINE"

    TAX_DB = {
        1: TaxNode(1, None),
        2: TaxNode(2, 1),
        3: TaxNode(3, 1),
        4: TaxNode(4, 2),
        5: TaxNode(5, 2),
        6: TaxNode(6, 4),
        7: TaxNode(7, 5),
    }
    taxa = build_taxa(TAX_DB)

    with FamDBRoot(f"{filename}.0.h5", "w") as db:
        db.set_metadata(0, FILE_INFO, *DB_INFO)
        write_test_metadata(db)
        db.write_repeatpeps(FAKE_REPPEPS)

        db.write_full_taxonomy(taxa, NODES)
        db.write_taxonomy(NODES[0])
        # db.write_taxa_names(taxa, NODES)

        db.add_family(families[0])
        db.add_family(families[1])
        db.add_family(families[2])

        db.finalize()

    with FamDBLeaf(f"{filename}.1.h5", "w") as db:
        db.set_metadata(1, FILE_INFO, *DB_INFO)
        write_test_metadata(db)

        db.write_taxonomy(NODES[1])

        db.add_family(families[3])
        db.add_family(families[5])

        db.finalize()

    with FamDBLeaf(f"{filename}.2.h5", "w") as db:
        db.set_metadata(2, FILE_INFO, *DB_INFO)
        write_test_metadata(db)

        db.write_taxonomy(NODES[2])

        db.add_family(families[4])

        db.finalize()


def init_single_file(n, db_dir, change_id=False):
    """This method mirrors the process of file creation from export_dfam.py, without export_families()"""
    TAX_DB = {
        1: TaxNode(1, None),
        2: TaxNode(2, 1),
        3: TaxNode(3, 1),
        4: TaxNode(4, 2),
        5: TaxNode(5, 2),
        6: TaxNode(6, 4),
        7: TaxNode(7, 5),
    }
    filename = f"{db_dir}.{n}.h5"
    taxa = build_taxa(TAX_DB)
    if n == 0:
        file = FamDBRoot(filename, "w")
        file.write_full_taxonomy(taxa, NODES)
        # file.write_taxa_names(taxa, {n: NODES[n] for n in NODES})
    else:
        file = FamDBLeaf(filename, "w")
    if change_id:
        file_info = deepcopy(FILE_INFO)
        file_info["meta"]["partition_id"] = "uuidYY"

    else:
        file_info = deepcopy(FILE_INFO)

    file.write_taxonomy(NODES[n])

    write_test_metadata(file)

    file.set_metadata(n, file_info, *DB_INFO)

    file.finalize()
