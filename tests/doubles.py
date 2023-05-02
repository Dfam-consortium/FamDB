"""
Fakes, stubs, etc. for use in testing FamDB
"""

import famdb
import json

from famdb_classes import FamDB, FamDBRoot
from famdb_helper_classes import TaxNode


# convenience function to generate a test family
def make_family(acc, clades, consensus, model):
    fam = famdb.Family()
    fam.accession = acc
    fam.name = "Test family " + acc
    fam.version = 1
    fam.clades = clades
    fam.consensus = consensus
    fam.model = model

    return fam


"""
       1
     /   \\
    4     3
   /  \\
  2	  *6
 /
5
"""
tax_db = {
    1: TaxNode(1, None),
    2: TaxNode(2, 4),
    3: TaxNode(3, 1),
    4: TaxNode(4, 1),
    5: TaxNode(5, 2),
    6: TaxNode(6, 4),
}
tax_names = {
    1: "root",
    2: "Genus",
    3: "Other Order",
    4: "Order",
    5: "Species",
    6: "Other Genus",
}

nodes = {0: [1, 3, 4], 1: [2, 5], 2: [6]}


def build_taxa(nodes):
    for node in nodes.values():
        if node.tax_id != 1:
            node.parent_node = nodes[node.parent_id]
            node.parent_node.children += [node]
        node.names += [["scientific name", tax_names[node.tax_id]]]
    return nodes


def init_db_file():
    filename = "/tmp/unittest"
    # 0 - root, 1 - search, 2 - other
    file_info = {
        "meta": {"id": "uuidXX", "db_version": "V1", "db_date": "2020-07-15"},
        "file_map": {
            0: {
                "T_root": 1,
                "filename": "unittest.0.h5",
                "F_roots": [],
                "T_root_name": "Root Node",
                "F_roots_names": [],
            },
            1: {
                "T_root": 2,
                "filename": "unittest.1.h5",
                "F_roots": [2],
                "T_root_name": "Search Node",
                "F_roots_names": [],
            },
            2: {
                "T_root": 6,
                "filename": "unittest.2.h5",
                "F_roots": [6],
                "T_root_name": "Other Node",
                "F_roots_names": ["Other Node"],
            },
        },
    }

    db_info = ("Test", "V1", "2020-07-15", "Test Database", "<copyright header>")

    families = [
        make_family("TEST0001", [1], "ACGT", "<model1>"),
        make_family("TEST0002", [2, 6], None, "<model2>"),
        make_family("TEST0003", [6], "GGTC", "<model3>"),
        make_family("TEST0004", [2], "CCCCTTTT", None),
        make_family("DR0000001", [6], "GCATATCG", None),
        make_family("DR_Repeat1", [5], "CGACTAT", None),
    ]
    families[1].name = None
    families[2].search_stages = "30,40"
    families[3].buffer_stages = "10[1-2],10[5-8],20"
    families[3].search_stages = "35"
    families[3].repeat_type = "SINE"

    taxa = build_taxa(tax_db)

    def write_test_metadata(db):
        # Override setting of format metadata for testing
        db.file.attrs["generator"] = "famdb.py v0.4.3"
        db.file.attrs["version"] = "0.5"
        db.file.attrs["created"] = "2023-01-09 09:57:56.026443"

    with FamDBRoot(f"{filename}.0.h5", "w") as db:
        db.set_db_info(*db_info)
        db.set_file_info(file_info)
        write_test_metadata(db)

        db.add_family(families[0])

        db.write_taxonomy(taxa, nodes[0])
        db.write_taxa_names(taxa, nodes)
        db.finalize()

    with FamDB(f"{filename}.1.h5", "w") as db:
        db.set_db_info(*db_info)
        db.set_file_info(file_info)
        write_test_metadata(db)

        db.add_family(families[1])
        db.add_family(families[3])
        db.add_family(families[5])

        db.write_taxonomy(taxa, nodes[1])
        db.finalize()

    with FamDB(f"{filename}.2.h5", "w") as db:
        db.set_db_info(*db_info)
        db.set_file_info(file_info)
        write_test_metadata(db)

        db.add_family(families[0])
        db.add_family(families[4])

        db.write_taxonomy(taxa, nodes[2])
        db.finalize()
