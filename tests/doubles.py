"""
Fakes, stubs, etc. for use in testing FamDB
"""
from copy import deepcopy
from famdb_classes import FamDBLeaf, FamDBRoot
from famdb_helper_classes import TaxNode, Family

"""
        1
      /   \\
 (0) 2     3
--------------
(1)/ |\\ (2)
  4	 | *5
 /   |
6    |
"""

TAX_NAMES = {
    1: "root",
    2: "Order",
    3: "Other Order",
    4: "Genus",
    5: "Other Genus",
    6: "Species",
}
COMMON_NAMES = {
    1: "Root Dummy 1",
    2: "Root Dummy 2",
    3: "Root Dummy 3",
    4: "Leaf Dummy 4",
    5: "Leaf Dummy 5",
    6: "Leaf Dummy 6",
}
# 0 - root, 1 - search, 2 - other
NODES = {0: [1, 2, 3], 1: [4, 6], 2: [5]}

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

DB_INFO = ("Test", "V1", "2020-07-15", "Test Database", "<copyright header>")


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


def init_db_file(filename):

    FAMILIES = [
        make_family("TEST0001", [1], "ACGT", "<model1>"),
        make_family("TEST0002", [2, 3], None, "<model2>"),
        make_family("TEST0003", [3], "GGTC", "<model3>"),
        make_family("TEST0004", [4], "CCCCTTTT", None),
        make_family("DR000000001", [5], "GCATATCG", None),
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
    }
    taxa = build_taxa(TAX_DB)

    def write_test_metadata(db):
        # Override setting of format metadata for testing
        db.file.attrs["generator"] = "famdb.py v1.0.1"
        db.file.attrs["version"] = "1.0"
        db.file.attrs["created"] = "2023-01-09 09:57:56.026443"

    with FamDBRoot(f"{filename}.0.h5", "w") as db:
        db.set_db_info(*DB_INFO)
        db.set_file_info(FILE_INFO)
        db.set_partition_info(0)
        write_test_metadata(db)

        db.write_taxonomy(taxa, NODES[0])
        db.write_taxa_names(taxa, NODES)

        db.add_family(families[0])
        db.add_family(families[1])
        db.add_family(families[2])

        db.finalize()

    with FamDBLeaf(f"{filename}.1.h5", "w") as db:
        db.set_db_info(*DB_INFO)
        db.set_file_info(FILE_INFO)
        db.set_partition_info(1)
        write_test_metadata(db)

        db.write_taxonomy(taxa, NODES[1])

        db.add_family(families[3])
        db.add_family(families[5])

        db.finalize()

    with FamDBLeaf(f"{filename}.2.h5", "w") as db:
        db.set_db_info(*DB_INFO)
        db.set_file_info(FILE_INFO)
        db.set_partition_info(2)
        write_test_metadata(db)

        db.write_taxonomy(taxa, NODES[2])

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
    }
    filename = f"{db_dir}.{n}.h5"
    taxa = build_taxa(TAX_DB)
    if n == 0:
        file = FamDBRoot(filename, "w")
        file.write_taxa_names(taxa, {n: NODES[n] for n in NODES})
    else:
        file = FamDBLeaf(filename, "w")
    file.set_partition_info(n)
    if change_id:
        new_info = deepcopy(FILE_INFO)
        new_info["meta"]["partition_id"] = "uuidYY"
        file.set_file_info(new_info)
    else:
        file.set_file_info(FILE_INFO)
    file.set_db_info(*DB_INFO)
    nodes = NODES[n]
    file.write_taxonomy(taxa, nodes)
    file.finalize()
