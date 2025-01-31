import os
import unittest
from famdb_classes import FamDBLeaf, FamDBRoot, FamDB
from famdb_helper_classes import Family
from .doubles import init_db_file, FILE_INFO
from unittest.mock import patch
import io
from famdb_globals import FAMDB_VERSION, TEST_DIR, DESCRIPTION


class TestDatabase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        file_dir = f"{TEST_DIR}/db"
        os.makedirs(file_dir, exist_ok=True)
        db_dir = f"{file_dir}/unittest"
        init_db_file(db_dir)
        filenames = [f"{db_dir}.0.h5", f"{db_dir}.1.h5", f"{db_dir}.2.h5"]
        TestDatabase.filenames = filenames
        TestDatabase.file_dir = file_dir
        TestDatabase.famdb = FamDB(file_dir, "r+")
        TestDatabase.famdb.build_pruned_tree()

    @classmethod
    def tearDownClass(cls):
        filenames = TestDatabase.filenames
        TestDatabase.filenames = None

        for name in filenames:
            os.remove(name)
        os.rmdir(TestDatabase.file_dir)

    def test_get_metadata(self):
        test_info = {
            "famdb_version": FAMDB_VERSION,
            "created": "<creation date>",
            "partition_name": "Search Node",
            "partition_detail": "",
            "name": "Test Dfam",
            "db_version": "V1",
            "date": "2020-07-15",
            "description": DESCRIPTION,
            "copyright": "<copyright header>",
        }

        with FamDBLeaf(TestDatabase.filenames[1], "r") as db:
            self.assertEqual(db.get_metadata(), test_info)

        test_info["partition_name"] = "Root Node"
        with FamDBRoot(TestDatabase.filenames[0], "r") as db:
            self.assertEqual(
                db.get_metadata(),
                test_info,
            )

    def test_get_history(self):
        substrings = [
            "File Initialized",
            "Metadata Set",
            "RepeatPeps Written",
            "Taxonomy Nodes Written",
            "Taxonomy Names Written",
        ]
        with FamDBRoot(TestDatabase.filenames[0], "r") as db:
            history = db.get_history()
            for substring in substrings:
                self.assertIn(substring, history)

    def test_interrupt_check(self):
        message = "Test Message"
        with FamDBRoot(TestDatabase.filenames[0], "r") as db:
            stamp = db.update_changelog(message)
            self.assertTrue(db.interrupt_check())
            db._verify_change(stamp, message)
            self.assertFalse(db.interrupt_check())

    def test_update_description(self):
        new_desc = "New Description"
        with FamDBRoot(TestDatabase.filenames[0], "r") as db:
            db.update_description(new_desc)
            self.assertEqual(db.get_metadata()["description"], new_desc)

    def test_get_counts(self):
        with FamDBRoot(TestDatabase.filenames[0], "r") as db:
            self.assertEqual(db.get_counts(), {"consensus": 2, "hmm": 3})

        with FamDBLeaf(TestDatabase.filenames[1], "r") as db:
            self.assertEqual(db.get_counts(), {"consensus": 2, "hmm": 0})

        with FamDBLeaf(TestDatabase.filenames[2], "r") as db:
            self.assertEqual(db.get_counts(), {"consensus": 1, "hmm": 0})

    def test_get_partition_num(self):
        with FamDBRoot(TestDatabase.filenames[0], "r") as db:
            self.assertEqual(db.get_partition_num(), 0)

        with FamDBLeaf(TestDatabase.filenames[1], "r") as db:
            self.assertEqual(db.get_partition_num(), 1)

        with FamDBLeaf(TestDatabase.filenames[2], "r") as db:
            self.assertEqual(db.get_partition_num(), 2)

    def test_get_file_info(self):
        with FamDBRoot(TestDatabase.filenames[0], "r") as db:
            self.assertDictEqual(db.get_file_info(), FILE_INFO)

    def test_is_root(self):
        with FamDBRoot(TestDatabase.filenames[0], "r") as db:
            self.assertEqual(db.is_root(), True)

        with FamDBLeaf(TestDatabase.filenames[1], "r") as db:
            self.assertEqual(db.is_root(), False)

    def test_get_family_by_accession(self):
        with FamDBRoot(TestDatabase.filenames[0], "r") as db:
            test_fam = db.get_family_by_accession("TEST0001")
            self.assertIsInstance(test_fam, Family)
            self.assertEqual(test_fam.name, "Test family TEST0001")
            self.assertEqual(db.get_family_by_accession("TEST0000"), None)

    def test_get_family_names(self):
        with FamDBRoot(TestDatabase.filenames[0], "r") as db:
            self.assertCountEqual(
                db.get_family_names(), ["Test family TEST0001", "Test family TEST0003"]
            )
        with FamDBLeaf(TestDatabase.filenames[1], "r") as db:
            self.assertCountEqual(
                db.get_family_names(),
                ["Test family TEST0004", "Test family DR_Repeat1"],
            )
        with FamDBLeaf(TestDatabase.filenames[2], "r") as db:
            self.assertCountEqual(db.get_family_names(), ["Test family DR000000001"])

    def test_get_family_by_name(self):
        with FamDBRoot(TestDatabase.filenames[0], "r") as db:
            self.assertEqual(db.get_family_by_name("Test family TEST0002"), None)
        with FamDBLeaf(TestDatabase.filenames[1], "r") as db:
            test_fam = db.get_family_by_name("Test family TEST0004")
            self.assertIsInstance(test_fam, Family)
            self.assertEqual(test_fam.name, "Test family TEST0004")

    def test_get_families_for_taxon(self):
        with FamDBRoot(TestDatabase.filenames[0], "r") as db:
            self.assertEqual(db.get_families_for_taxon(3), ["TEST0002", "TEST0003"])

        with FamDBLeaf(TestDatabase.filenames[1], "r") as db:
            self.assertEqual(db.get_families_for_taxon(4), ["TEST0004"])

    def test_get_complete_lineage(self):
        with FamDBRoot(TestDatabase.filenames[0], "r") as db:
            self.assertEqual(db.get_lineage(4), [4])
            self.assertEqual(
                db.get_lineage(4, descendants=True, complete=True), [4, [6]]
            )
            self.assertEqual(
                db.get_lineage(6, ancestors=True, complete=True),
                [1, [2, [4, [6]]]],
            )
            self.assertEqual(
                db.get_lineage(4, ancestors=True, descendants=True, complete=True),
                [1, [2, [4, [6]]]],
            )

            self.assertEqual(db.get_lineage(1, complete=True), [1])
            self.assertEqual(
                db.get_lineage(1, descendants=True, complete=True),
                [1, [2, [4, [6]], [5, [7]]], [3]],
            )
            self.assertEqual(
                db.get_lineage(2, ancestors=True, descendants=True, complete=True),
                 [1, [2, [4, [6]], [5, [7]]]],
            )

            self.assertEqual(
                db.get_lineage(5, descendants=True, complete=False), [5, [7]]
            )
            self.assertEqual(
                db.get_lineage(7, ancestors=True, complete=False),
                [1, [2, [7]]],
            )
            self.assertEqual(
                db.get_lineage(5, ancestors=True, complete=False),
                 [1, [2, [5]]],
            )

            self.assertEqual(
                db.get_lineage(1, descendants=True, complete=False),
                [1, [2, [4, [6]], [7]], [3]],
            )
            self.assertEqual(
                db.get_lineage(3, ancestors=True, complete=False), [1, [3]]
            )
            self.assertEqual( 
                db.get_lineage(2, ancestors=True, descendants=True, complete=False),
                [1, [2, [4, [6]], [7]]],
            )

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
                    [5, False, 2],
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
            self.assertEqual(db.get_taxon_name(10), ("Not Found", "N/A"))
            self.assertEqual(db.get_taxon_name(2, "common name"), ["Root Dummy 2", 0])
            self.assertEqual(db.get_taxon_name(4), ["Genus", 1])

    def test_get_taxon_names(self):
        with FamDBRoot(TestDatabase.filenames[0], "r") as db:
            self.assertEqual(
                db.get_taxon_names(2),
                [["scientific name", "Order"], ["common name", "Root Dummy 2"]],
            )
            self.assertEqual(
                db.get_taxon_names(4),
                [["scientific name", "Genus"], ["common name", "Leaf Dummy 4"]],
            )
            self.assertEqual(db.get_taxon_names(10), [])

    def test_get_lineage_path(self):
        with FamDBRoot(TestDatabase.filenames[0], "r") as db:
            self.assertEqual(
                db.get_lineage_path(3, complete=True), [["root", 0], ["Other Order", 0]]
            )

            # test caching in get_lineage_path
            self.assertEqual(
                db.get_lineage_path(3, complete=True), [["root", 0], ["Other Order", 0]]
            )

            # test lookup without cache
            self.assertEqual(
                db.get_lineage_path(3, cache=False, complete=True),
                [["root", 0], ["Other Order", 0]],
            )

            # test with supplied tree
            self.assertEqual(
                db.get_lineage_path(4, [1, [2, [4]], [3]], complete=True),
                [["root", 0], ["Order", 0], ["Genus", 1]],
            )

    def test_resolve_species(self):
        with FamDBRoot(TestDatabase.filenames[0], "r") as db:
            self.assertEqual(db.resolve_species(3), [[3, 0, True]])
            self.assertEqual(db.resolve_species(4), [[4, 1, True]])
            self.assertEqual(db.resolve_species(999), [])
            self.assertEqual(
                db.resolve_species("Species"), [[6, 1, True], [7, 2, False]]
            )
            self.assertEqual(db.resolve_species("Tardigrade"), [])

    def test_resolve_one_species(self):
        with FamDBRoot(TestDatabase.filenames[0], "r") as db:
            self.assertEqual(db.resolve_one_species(3), [3, 0])
            self.assertEqual(db.resolve_one_species(999), (None, None))
            self.assertEqual(db.resolve_one_species("Species"), [6, 1])
            self.assertEqual(db.resolve_one_species("Mus musculus"), (None, None))

    def test_get_sanitized_name(self):
        with FamDBRoot(TestDatabase.filenames[0], "r") as db:
            self.assertEqual(db.get_sanitized_name(5), "Other_Genus")

    def test_find_files(self):
        with FamDBRoot(TestDatabase.filenames[0], "r") as db:
            self.assertEqual(db.get_file_info(), FILE_INFO)

    def test_find_taxon(self):
        with FamDBRoot(TestDatabase.filenames[0], "r") as db:
            self.assertEqual(db.find_taxon(2), 0)
            self.assertEqual(db.find_taxon(4), 1)
            self.assertEqual(db.find_taxon(5), 2)

    def test_repeatpeps(self):
        with FamDBRoot(TestDatabase.filenames[0], "r") as db:
            self.assertEqual(db.get_repeatpeps(), ">DUMMYACC\nDUMMYDATA")

    # Umbrella Methods -----------------------------------------------------------------------------
    def test_get_lineage(self):
        famdb = TestDatabase.famdb
        self.assertEqual(famdb.get_lineage(4), [4])
        self.assertEqual(
            famdb.get_lineage(4, descendants=True, complete=True), [4, [6]]
        )
        self.assertEqual(
            famdb.get_lineage(6, ancestors=True, complete=True),
            [1, [2, [4, [6]]]],
        )
        self.assertEqual(
            famdb.get_lineage(4, ancestors=True, descendants=True, complete=True),
            [1, [2, [4, [6]]]],
        )

        self.assertEqual(famdb.get_lineage(1, complete=True), [1])
        self.assertEqual(
            famdb.get_lineage(1, descendants=True, complete=True),
            [1, [2, [4, [6]], [5, [7]]], [3]],
        )
        self.assertEqual(
            famdb.get_lineage(2, ancestors=True, descendants=True, complete=True),
            [1, [2, [4, [6]], [5, [7]]]],
        )

        self.assertEqual(
            famdb.get_lineage(5, descendants=True, complete=False), [5, [7]]
        )
        self.assertEqual( 
            famdb.get_lineage(7, ancestors=True, complete=False),
            [1, [2, [7]]],
        )
        self.assertEqual(
            famdb.get_lineage(5, ancestors=True, complete=False),
            [1, [2, [5]]],
        )

        self.assertEqual(
            famdb.get_lineage(1, descendants=True, complete=False),
            [1, [2, [4, [6]], [7]], [3]],
        )
        self.assertEqual(
            famdb.get_lineage(3, ancestors=True, complete=False), [1, [3]]
        )
        self.assertEqual(
            famdb.get_lineage(2, ancestors=True, descendants=True, complete=False),
            [1, [2, [4, [6]], [7]]],
        )

    @patch("sys.stdout", new_callable=io.StringIO)
    def test_show_files(self, mock_print):
        famdb = TestDatabase.famdb
        famdb.show_files()
        out = f"""\nPartition Details
-----------------
 Partition 0 [unittest.0.h5]: Root Node 
     Consensi: 2, HMMs: 3

 Partition 1 [unittest.1.h5]: Search Node 
     Consensi: 2, HMMs: 0

 Partition 2 [unittest.2.h5]: Other Node - Other Node
     Consensi: 1, HMMs: 0\n
"""
        self.assertEqual(mock_print.getvalue(), out)

    def test_get_complete_lineage_path(self):
        famdb = TestDatabase.famdb
        self.assertEqual(
            famdb.get_lineage_path(5, cache=False, complete=True),
            [["root", 0], ["Order", 0], ["Other Genus", 2]],
        ) 
        self.assertEqual(
            famdb.get_lineage_path(
                5, partition=False, cache=False, complete=True
            ),
            ["root", "Order", "Other Genus"],
        )

    def test_get_pruned_lineage_path(self):
        famdb = TestDatabase.famdb
        self.assertEqual(
            famdb.get_lineage_path(7, complete=False),
            [["root", 0], ["Order", 0], ["Other Species", 2]],
        ) 
        self.assertEqual(
            famdb.get_lineage_path(5, complete=False),
            [["root", 0], ["Order", 0], ["Other Genus", 2]],
        ) 
        self.assertEqual(
            famdb.get_lineage_path(5,  partition=False, cache=False, complete=False),
            ["root", "Order", "Other Genus"],
        ) 

    def test_get_counts(self):
        famdb = TestDatabase.famdb
        self.assertEqual(famdb.get_counts(), {"consensus": 5, "hmm": 3, "file": 3})

    def test_resolve_names(self):
        famdb = TestDatabase.famdb
        self.assertEqual(
            famdb.resolve_names(4),
            [
                [
                    4,
                    True,
                    1,
                    [["scientific name", "Genus"], ["common name", "Leaf Dummy 4"]],
                ]
            ],
        )
        self.assertEqual(
            famdb.resolve_names(2),
            [
                [
                    2,
                    True,
                    0,
                    [["scientific name", "Order"], ["common name", "Root Dummy 2"]],
                ]
            ],
        )
        self.assertEqual(
            famdb.resolve_names("Order"),
            [
                [
                    2,
                    True,
                    0,
                    [["scientific name", "Order"], ["common name", "Root Dummy 2"]],
                ],
                [
                    3,
                    False,
                    0,
                    [
                        ["scientific name", "Other Order"],
                        ["common name", "Root Dummy 3"],
                    ],
                ],
            ],
        )
        self.assertEqual(
            famdb.resolve_names("Other Order"),
            [
                [
                    3,
                    True,
                    0,
                    [
                        ["scientific name", "Other Order"],
                        ["common name", "Root Dummy 3"],
                    ],
                ]
            ],
        )

    def test_get_accessions_filtered(self):
        famdb = TestDatabase.famdb

        self.assertEqual(
            sorted(list(famdb.get_accessions_filtered())),
            [
                "DR000000001",
                "DR_Repeat1",
                "TEST0001",
                "TEST0002",
                "TEST0003",
                "TEST0004",
            ],
        )
        self.assertEqual(
            list(famdb.get_accessions_filtered(tax_id=3)),
            ["TEST0002", "TEST0003"],
        )
        self.assertEqual(
            list(famdb.get_accessions_filtered(tax_id=3, ancestors=True)),
            ["TEST0001", "TEST0002", "TEST0003"],
        )
        self.assertEqual(list(famdb.get_accessions_filtered(stage=30)), ["TEST0003"])
        self.assertEqual(list(famdb.get_accessions_filtered(stage=60)), [])
        self.assertEqual(
            list(famdb.get_accessions_filtered(is_hmm=True, stage=10)),
            [],
        )
        self.assertEqual(
            list(famdb.get_accessions_filtered(is_hmm=False, stage=10)),
            ["TEST0004"],
        )
        self.assertEqual(list(famdb.get_accessions_filtered(stage=10, is_hmm=True)), [])
        self.assertEqual(
            list(famdb.get_accessions_filtered(name="Test family TEST0004")),
            ["TEST0004"],
        )
        self.assertEqual(
            list(famdb.get_accessions_filtered(repeat_type="SINE")), ["TEST0004"]
        )

        self.assertEqual(
            list(famdb.get_accessions_filtered(tax_id=4, descendants=True)),
            ["TEST0004", "DR_Repeat1"],
        )
        # curated/uncurated are backwards because it's easier than rewriting all the family names and all the tests
        self.assertEqual(
            list(famdb.get_accessions_filtered(uncurated_only=True)),
            ["DR000000001"],
        )
        self.assertEqual(
            list(famdb.get_accessions_filtered(curated_only=True)),
            ["TEST0001", "TEST0002", "TEST0003", "DR_Repeat1", "TEST0004"],
        )
