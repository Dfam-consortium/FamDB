import json
import os
import tempfile
import unittest

from famdb import Family, FamDB
from .doubles import init_db_file

class TestDatabase(unittest.TestCase):
    # Set up a single database file shared by all tests in this class
    @classmethod
    def setUpClass(cls):
        fd, filename = tempfile.mkstemp()
        os.close(fd)

        init_db_file(filename)
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
                "consensus": 5,
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
                    [7, False],
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

            self.assertEqual(db.resolve_species("Drosophila", kind="scientific name"), [[5, True], [6, True], [7, False]])
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
                ["DR0000001", "DR_Repeat1", "TEST0001", "TEST0002", "TEST0003", "TEST0004"],
            )
            self.assertEqual(list(db.get_accessions_filtered(stage=30)), ["TEST0003"])
            self.assertEqual(list(db.get_accessions_filtered(stage=10)), ["TEST0004"])
            self.assertEqual(list(db.get_accessions_filtered(stage=10, is_hmm=True)), [])
            self.assertEqual(list(db.get_accessions_filtered(name="Test family TEST0004")), ["TEST0004"])
            self.assertEqual(list(db.get_accessions_filtered(repeat_type="SINE")), ["TEST0004"])
            self.assertEqual(list(db.get_accessions_filtered(stage=80, tax_id=2)), ["TEST0002", "TEST0004"])
            self.assertEqual(list(db.get_accessions_filtered(stage=95, tax_id=2)), ["TEST0004"])
            self.assertEqual(list(db.get_accessions_filtered(tax_id=6, curated_only=True)), [])
            self.assertEqual(list(db.get_accessions_filtered(tax_id=6, curated_only=False)), ["DR0000001"])
            self.assertEqual(list(db.get_accessions_filtered(tax_id=5, curated_only=True)), ["DR_Repeat1"])

    def test_lineage(self):
        with FamDB(TestDatabase.filename, "r") as db:
            self.assertEqual(db.get_lineage(1, descendants=True), [1, [2], [3, [5, [7]], [6]]])
            self.assertEqual(db.get_lineage(3), [3])
            self.assertEqual(db.get_lineage(6, ancestors=True), [1, [3, [6]]])

            self.assertEqual(db.get_lineage_path(3), ["root", "Third Clade"])

            # test caching in get_lineage_path
            self.assertEqual(db.get_lineage_path(3), ["root", "Third Clade"])

            # test lookup without cache
            self.assertEqual(db.get_lineage_path(3, False), ["root", "Third Clade"])
