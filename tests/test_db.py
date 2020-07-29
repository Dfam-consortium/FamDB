import json
import os
import tempfile
import unittest

from famdb import Family, FamDB

# lightweight taxonomy node with the minimum required by FamDB
class TaxNode:
    def __init__(self, tax_id, parent, sci_name):
        self.tax_id = tax_id
        if parent is None:
            self.parent_id = None
        else:
            self.parent_id = parent.tax_id
        self.names = [["scientific name", sci_name]]

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
    # Set up a single database file shared by all tests in this class
    @classmethod
    def setUpClass(cls):
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
            families[3].search_stages = "35"
            families[3].repeat_type = "SINE"

            for fam in families:
                db.add_family(fam)

            taxa = {}
            taxa[1] = TaxNode(1, None, "root")
            taxa[2] = TaxNode(2, taxa[1], "Clade 2")
            taxa[3] = TaxNode(3, taxa[1], "Third Clade")
            taxa[4] = TaxNode(4, taxa[3], "Unused Clade")
            taxa[4].used = False
            taxa[5] = TaxNode(5, taxa[3], "Drosophila <flies>")
            taxa[6] = TaxNode(6, taxa[3], "Drosophila <fungus>")

            db.write_taxonomy(taxa)
            db.finalize()

        TestDatabase.filename = filename

    @classmethod
    def tearDownClass(cls):
        filename = TestDatabase.filename
        TestDatabase.filename = None

        os.remove(filename)

    def test_metadata(self):
        with FamDB(TestDatabase.filename, "r") as db:
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

    def test_species_lookup(self):
        with FamDB(TestDatabase.filename, "r") as db:
            self.assertEqual(list(db.search_taxon_names("Clade")), [
                [2, False],
                [3, False],
            ])

            self.assertEqual(list(db.search_taxon_names("Third Clade")), [
                [3, True],
            ])

            self.assertEqual(list(db.search_taxon_names("Tardigrade", search_similar=True)), [
                [3, False],
            ])

            self.assertEqual(
                list(db.search_taxon_names("Drosophila", "scientific name")),
                [
                    [5, True],
                    [6, True],
                ]
            )

            # TODO: not being tested: some of these print disambiguations to stdout

            self.assertEqual(db.resolve_species(3), [[3, True]])
            self.assertEqual(db.resolve_one_species(3), 3)
            self.assertEqual(db.resolve_species(999), [])
            self.assertEqual(db.resolve_one_species(999), None)

            self.assertEqual(db.resolve_species("Tardigrade"), [])
            self.assertEqual(db.resolve_one_species("Tardigrade"), None)

            self.assertEqual(db.resolve_species("Mus musculus"), [])
            self.assertEqual(db.resolve_one_species("Mus musculus"), None)

            self.assertEqual(db.resolve_species("Tardigrade", search_similar=True), [[3, False]])
            self.assertEqual(db.resolve_one_species("Tardigrade"), None)

            self.assertEqual(db.resolve_species("Drosophila", kind="scientific name"), [[5, True], [6, True]])
            self.assertEqual(db.resolve_one_species("Drosophila", kind="scientific name"), None)

            self.assertEqual(db.resolve_species("hird"), [[3, False]])
            self.assertEqual(db.resolve_one_species("hird"), 3)

    def test_taxa_queries(self):
        with FamDB(TestDatabase.filename, "r") as db:
            self.assertEqual(db.get_taxon_name(3), "Third Clade")
            self.assertEqual(db.get_sanitized_name(5), "Drosophila_flies")

    def test_family_queries(self):
        with FamDB(TestDatabase.filename, "r") as db:
            self.assertEqual(list(db.get_families_for_taxon(3)), ["TEST0002", "TEST0003"])
            self.assertEqual(
                list(db.get_accessions_filtered(tax_id=3)),
                ["TEST0002", "TEST0003"],
            )
            self.assertEqual(
                list(db.get_accessions_filtered(tax_id=3, ancestors=True)),
                ["TEST0001", "TEST0002", "TEST0003"],
            )
            self.assertEqual(
                sorted(list(db.get_accessions_filtered())),
                ["TEST0001", "TEST0002", "TEST0003", "TEST0004"],
            )
            self.assertEqual(list(db.get_accessions_filtered(stage=30)), ["TEST0003"])
            self.assertEqual(list(db.get_accessions_filtered(stage=10)), ["TEST0004"])
            self.assertEqual(list(db.get_accessions_filtered(stage=10, is_hmm=True)), [])
            self.assertEqual(list(db.get_accessions_filtered(name="Test family TEST0004")), ["TEST0004"])
            self.assertEqual(list(db.get_accessions_filtered(repeat_type="SINE")), ["TEST0004"])
            self.assertEqual(list(db.get_accessions_filtered(stage=80, tax_id=2)), ["TEST0002", "TEST0004"])
            self.assertEqual(list(db.get_accessions_filtered(stage=95, tax_id=2)), ["TEST0004"])

    def test_lineage(self):
        with FamDB(TestDatabase.filename, "r") as db:
            self.assertEqual(db.get_lineage(1, descendants=True), [1, [2], [3, [5], [6]]])
            self.assertEqual(db.get_lineage(3), [3])
            self.assertEqual(db.get_lineage(6, ancestors=True), [1, [3, [6]]])

            self.assertEqual(db.get_lineage_path(3), ["root", "Third Clade"])

            # test caching in get_lineage_path
            self.assertEqual(db.get_lineage_path(3), ["root", "Third Clade"])

            # test lookup without cache
            self.assertEqual(db.get_lineage_path(3, False), ["root", "Third Clade"])
