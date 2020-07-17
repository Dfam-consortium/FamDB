import json
import os
import tempfile
import unittest

from famdb import Family, FamDB

# lightweight taxonomy node with the minimum required by
class TaxNode:
    def __init__(self, tax_id, parent, sci_name):
        self.tax_id = tax_id
        if parent is None:
            self.parent_id = None
        else:
            self.parent_id = parent.tax_id
        self.names = [["scientific name"], sci_name]

        self.parent_node = parent
        self.children = []
        self.used = True

        if parent:
            parent.children.append(self)

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

class TestDatabase(unittest.TestCase):
    def test_metadata(self):
        fd, filename = tempfile.mkstemp()
        os.close(fd)

        with FamDB(filename, "w") as db:
            db.set_db_info("Test", "V1", "2020-07-15", "Test Database", "<copyright header>")

            families = [
                make_family("TEST0001", [1], "ACGT", "<model1>"),
                make_family("TEST0002", [2, 3], None, "<model2>"),
                make_family("TEST0003", [3], "GGTC", "<model3>"),
                make_family("TEST0004", [2], "CCCCTTTT", None),
            ]

            families[1].name = None
            families[2].search_stages = "30,40"
            families[3].buffer_stages = "10[1-2],10[5-8],20"

            for fam in families:
                db.add_family(fam)

            root = TaxNode(1, None, "root")
            t2 = TaxNode(2, root, "Clade 2")
            t3 = TaxNode(3, root, "Third Clade")
            t4 = TaxNode(4, t3, "Unused Clade")
            t4.used = False

            db.write_taxonomy({1: root, 2: t2, 3: t3, 4: t4})
            db.finalize()

        with FamDB(filename, "r") as db:
            self.assertEqual(db.get_db_info(), {
                "name": "Test",
                "version": "V1",
                "date": "2020-07-15",
                "description": "Test Database",
                "copyright": "<copyright header>",
            })
            self.assertEqual(db.get_counts(), {
                "consensus": 3,
                "hmm": 3,
            })

        os.remove(filename)
