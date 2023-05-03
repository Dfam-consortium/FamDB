import os
import unittest

from famdb_classes import FamDB, FamDBRoot
from .doubles import init_db_file, FILE_INFO, FAMILIES

# from famdb_helper_classes import Family


class TestDatabase(unittest.TestCase):
    # Set up a single database file shared by all tests in this class
    @classmethod
    def setUpClass(cls):

        filenames = ["/tmp/unittest.0.h5", "/tmp/unittest.1.h5", "/tmp/unittest.2.h5"]
        init_db_file()
        TestDatabase.filenames = filenames

    @classmethod
    def tearDownClass(cls):
        filenames = TestDatabase.filenames
        TestDatabase.filenames = None

        for name in filenames:
            os.remove(name)

    def test_get_db_info(self):
        test_info = {
            "name": "Test",
            "version": "V1",
            "date": "2020-07-15",
            "description": "Test Database",
            "copyright": "<copyright header>",
        }
        with FamDB(TestDatabase.filenames[1], "r") as db:
            self.assertEqual(db.get_db_info(), test_info)

        with FamDBRoot(TestDatabase.filenames[0], "r") as db:
            self.assertEqual(
                db.get_db_info(),
                test_info,
            )

    def test_get_counts(self):
        with FamDBRoot(TestDatabase.filenames[0], "r") as db:
            self.assertEqual(db.get_counts(), {"consensus": 2, "hmm": 3})

        with FamDB(TestDatabase.filenames[1], "r") as db:
            self.assertEqual(db.get_counts(), {"consensus": 2, "hmm": 0})

        with FamDB(TestDatabase.filenames[2], "r") as db:
            self.assertEqual(db.get_counts(), {"consensus": 1, "hmm": 0})

    def test_get_partition_num(self):
        with FamDBRoot(TestDatabase.filenames[0], "r") as db:
            self.assertEqual(db.get_partition_num(), 0)

        with FamDB(TestDatabase.filenames[1], "r") as db:
            self.assertEqual(db.get_partition_num(), 1)

        with FamDB(TestDatabase.filenames[2], "r") as db:
            self.assertEqual(db.get_partition_num(), 2)

    def test_get_file_info(self):
        with FamDBRoot(TestDatabase.filenames[0], "r") as db:
            self.assertDictEqual(db.get_file_info(), FILE_INFO)

    def test_is_root(self):
        with FamDBRoot(TestDatabase.filenames[0], "r") as db:
            self.assertEqual(db.is_root(), True)

        with FamDB(TestDatabase.filenames[1], "r") as db:
            self.assertEqual(db.is_root(), False)

    def test_get_metadata(self):
        with FamDBRoot(TestDatabase.filenames[0], "r") as db:
            self.assertEqual(
                db.get_metadata(),
                {
                    "generator": "famdb.py v0.4.3",
                    "version": "0.5",
                    "created": "2023-01-09 09:57:56.026443",
                    "partition_name": "Root Node",
                    "partition_detail": "",
                },
            )
        with FamDB(TestDatabase.filenames[1], "r") as db:
            self.assertEqual(
                db.get_metadata(),
                {
                    "generator": "famdb.py v0.4.3",
                    "version": "0.5",
                    "created": "2023-01-09 09:57:56.026443",
                    "partition_name": "Search Node",
                    "partition_detail": "",
                },
            )

    # def test_get_family_names(self):
    #     with FamDBRoot(TestDatabase.filenames[0], "r") as db:
    #         self.assertCountEqual(db.get_family_names(), ['Test family TEST0001','Test family TEST0002', 'Test family TEST0003']) # TODO solve this
    #     with FamDB(TestDatabase.filenames[1], "r") as db:
    #         self.assertCountEqual(db.get_family_names(), ['Test family TEST0004', 'Test family DR0000001'])
    #     with FamDB(TestDatabase.filenames[2], "r") as db:
    #         self.assertCountEqual(db.get_family_names(), ['Test family DR_Repeat1'])

    # def test_get_family_by_accession(self):
    #     with FamDBRoot(TestDatabase.filenames[0], "r") as db:
    #         self.assertEqual(db.get_family_by_accession('TEST0001'), FAMILIES[0]) # TODO
    #     with FamDB(TestDatabase.filenames[1], "r") as db:
    #         self.assertEqual(db.get_family_by_accession('TEST0004'), 'Test family TEST0004')

    # def test_get_family_by_name(self):
    # with FamDBRoot(TestDatabase.filenames[0], "r") as db:
    #     self.assertEqual(db.get_family_by_name('Test family TEST0001'), 'Test family TEST0001') # TODO
    # with FamDB(TestDatabase.filenames[1], "r") as db:
    #     self.assertEqual(db.get_family_by_name('Test family TEST0004'), 'Test family TEST0004')

    def test_get_families_for_taxon(self):
        with FamDBRoot(TestDatabase.filenames[0], "r") as db:
            self.assertEqual(db.get_families_for_taxon(3), ["TEST0002", "TEST0003"])

        with FamDB(TestDatabase.filenames[1], "r") as db:
            self.assertEqual(db.get_families_for_taxon(4), ["TEST0004"])

    def test_get_accessions_filtered(self):
        pass

    # self.assertEqual(
    #         #     list(db.get_accessions_filtered(tax_id=3)),
    #         #     ["TEST0002", "TEST0003"],
    #         # )
    #         # self.assertEqual(
    #         #     list(db.get_accessions_filtered(tax_id=3, ancestors=True)),
    #         #     ["TEST0001", "TEST0002", "TEST0003"],
    #         # )

    #         #
    #         # self.assertEqual(
    #         #     sorted(list(db.get_accessions_filtered())),
    #         #     [
    #         #         "DR0000001",
    #         #         "DR_Repeat1",
    #         #         "TEST0001",
    #         #         "TEST0002",
    #         #         "TEST0003",
    #         #         "TEST0004",
    #         #     ],
    #         # )
    #         # self.assertEqual(list(db.get_accessions_filtered(stage=30)), ["TEST0003"])
    #         # self.assertEqual(list(db.get_accessions_filtered(stage=10)), ["TEST0004"])
    #         # self.assertEqual(
    #         #     list(db.get_accessions_filtered(stage=10, is_hmm=True)), []
    #         # )
    #         self.assertEqual(
    #             list(db.get_accessions_filtered(name="Test family TEST0004")),
    #             ["TEST0004"],
    #         )
    #         self.assertEqual(
    #             list(db.get_accessions_filtered(repeat_type="SINE")), ["TEST0004"]
    #         )
    #         # self.assertEqual(
    #         #     list(db.get_accessions_filtered(stage=80, tax_id=2)),
    #         #     ["TEST0002", "TEST0004"],
    #         # )
    #         # self.assertEqual(
    #         #     list(db.get_accessions_filtered(stage=95, tax_id=2)), ["TEST0004"]
    #         # )
    #         self.assertEqual(
    #             list(db.get_accessions_filtered(tax_id=6, curated_only=True)), []
    #         )
    #         self.assertEqual(
    #             list(db.get_accessions_filtered(tax_id=6, curated_only=False)),
    #             ["DR0000001"],
    #         )
    #         self.assertEqual(
    #             list(db.get_accessions_filtered(tax_id=5, curated_only=True)),
    #             ["DR_Repeat1"],
    #         )

    # Root File Methods ------------------------------------------------
    def test_search_taxon_names(self):
        with FamDBRoot(TestDatabase.filenames[0], "r") as db:
            self.assertEqual(
                list(db.search_taxon_names("Order")),
                [
                    [2, True, 0],
                    [3, False, 0],
                ],
            )

            self.assertEqual(
                list(db.search_taxon_names("Genus")),
                [
                    [4, True, 1],
                    [6, False, 2],
                ],
            )

            self.assertEqual(
                list(db.search_taxon_names("rut", search_similar=True)),
                [
                    [1, False, 0],
                ],
            )

            self.assertEqual(
                list(db.search_taxon_names("Root Dummy", "common name")),
                [
                    [1, False, 0],
                    [2, False, 0],
                    [3, False, 0],
                ],
            )

            self.assertEqual(list(db.search_taxon_names("Missing")), [])

    def test_get_taxon_name(self):
        with FamDBRoot(TestDatabase.filenames[0], "r") as db:
            self.assertEqual(db.get_taxon_name(2), ["Order", 0])
            self.assertEqual(db.get_taxon_name(10), None)
            self.assertEqual(db.get_taxon_name(2, "common name"), ["Root Dummy 2", 0])
            self.assertEqual(db.get_taxon_name(4), ["Genus", 1])

    def test_get_taxon_names(self):
        with FamDBRoot(TestDatabase.filenames[0], "r") as db:
            self.assertEqual(
                db.get_taxon_names(2),
                [["scientific name", "Order"], ["common name", "Root Dummy 2"], 0],
            )
            self.assertEqual(
                db.get_taxon_names(4),
                [["scientific name", "Genus"], ["common name", "Leaf Dummy 4"], 1],
            )
            self.assertEqual(db.get_taxon_names(10), [])

    def test_resolve_one_species(self):
        pass

    #         self.assertEqual(db.resolve_one_species(3), 3)
    #         self.assertEqual(db.resolve_one_species(999), None)
    #         self.assertEqual(db.resolve_one_species("Tardigrade"), None)
    #         self.assertEqual(db.resolve_one_species("Mus musculus"), None)

    def test_resolve_species(self):
        pass

    #         self.assertEqual(db.resolve_species(3), [[3, True]])
    #         self.assertEqual(db.resolve_species(999), [])
    #         self.assertEqual(db.resolve_species("Mus musculus"), [])
    #         self.assertEqual(db.resolve_species("Tardigrade"), [])

    def test_get_sanitized_name(self):
        pass

    def test_get_lineage_path(self):
        pass

    # def test_lineage(self):
    #     with FamDBRoot(TestDatabase.filenames[0], "r") as db:
    #         self.assertEqual(
    #             db.get_lineage(1, descendants=True), [1, [4, [2, [5]], [6]], [3]]
    #         )
    #         self.assertEqual(db.get_lineage(3), [3])
    #         self.assertEqual(db.get_lineage(6, ancestors=True), [1, [3, [6]]])

    #         self.assertEqual(db.get_lineage_path(3), ["root", "Third Clade"])

    #         # test caching in get_lineage_path
    #         self.assertEqual(db.get_lineage_path(3), ["root", "Third Clade"])

    #         # test lookup without cache
    #         self.assertEqual(db.get_lineage_path(3, False), ["root", "Third Clade"])

    def test_find_files(self):
        pass
