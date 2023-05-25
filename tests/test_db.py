import os
import unittest
from famdb_classes import FamDBLeaf, FamDBRoot, FamDB
from famdb_helper_classes import Lineage, Family
from .doubles import init_db_file, FILE_INFO
from unittest.mock import patch
import io


class TestDatabase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        file_dir = "/tmp/db"
        os.makedirs(file_dir)
        db_dir = f"{file_dir}/unittest"
        init_db_file(db_dir)
        filenames = [f"{db_dir}.0.h5", f"{db_dir}.1.h5", f"{db_dir}.2.h5"]
        TestDatabase.filenames = filenames
        TestDatabase.file_dir = file_dir

    @classmethod
    def tearDownClass(cls):
        filenames = TestDatabase.filenames
        TestDatabase.filenames = None

        for name in filenames:
            os.remove(name)
        os.rmdir(TestDatabase.file_dir)

    def test_get_db_info(self):
        test_info = {
            "name": "Test",
            "version": "V1",
            "date": "2020-07-15",
            "description": "Test Database",
            "copyright": "<copyright header>",
        }
        with FamDBLeaf(TestDatabase.filenames[1], "r") as db:
            self.assertEqual(db.get_db_info(), test_info)

        with FamDBRoot(TestDatabase.filenames[0], "r") as db:
            self.assertEqual(
                db.get_db_info(),
                test_info,
            )

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
        with FamDBLeaf(TestDatabase.filenames[1], "r") as db:
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
            self.assertCountEqual(db.get_family_names(), ["Test family DR0000001"])

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

    def test_get_accessions_filtered(self):
        with FamDBRoot(TestDatabase.filenames[0], "r") as db:
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
                [
                    "TEST0001",
                    "TEST0002",
                    "TEST0003",
                ],
            )
            self.assertEqual(list(db.get_accessions_filtered(stage=30)), ["TEST0003"])
            self.assertEqual(list(db.get_accessions_filtered(stage=20)), [])
            self.assertEqual(
                list(db.get_accessions_filtered(is_hmm=True)),
                ["TEST0001", "TEST0002", "TEST0003"],
            )

        with FamDBLeaf(TestDatabase.filenames[1], "r") as db:
            self.assertEqual(
                sorted(list(db.get_accessions_filtered())),
                [
                    "DR_Repeat1",
                    "TEST0004",
                ],
            )
            self.assertEqual(
                list(db.get_accessions_filtered(stage=10, is_hmm=True)), []
            )
            self.assertEqual(
                list(db.get_accessions_filtered(name="Test family TEST0004")),
                ["TEST0004"],
            )
            self.assertEqual(
                list(db.get_accessions_filtered(repeat_type="SINE")), ["TEST0004"]
            )

            self.assertEqual(
                list(db.get_accessions_filtered(tax_id=4, descendants=True)),
                ["TEST0004", "DR_Repeat1"],
            )
        with FamDBLeaf(TestDatabase.filenames[2], "r") as db:
            self.assertEqual(
                list(db.get_accessions_filtered(curated_only=True)),
                ["DR0000001"],
            )
            self.assertEqual(
                list(db.get_accessions_filtered(uncurated_only=True)),
                [],
            )

    def test_get_lineage(self):
        with FamDBLeaf(TestDatabase.filenames[1], "r") as db:
            self.assertEqual(db.get_lineage(4), [4])
            self.assertEqual(db.get_lineage(4, descendants=True), [4, [6]])
            self.assertEqual(
                db.get_lineage(6, ancestors=True), ["root_link:4", [4, [6]]]
            )
            self.assertEqual(
                db.get_lineage(4, ancestors=True, descendants=True),
                ["root_link:4", [4, [6]]],
            )

        with FamDBRoot(TestDatabase.filenames[0], "r") as db:
            self.assertEqual(db.get_lineage(1), [1])
            self.assertEqual(
                db.get_lineage(1, descendants=True),
                [1, [2, "leaf_link:4", "leaf_link:5"], [3]],
            )
            self.assertEqual(db.get_lineage(3, ancestors=True), [1, [3]])
            self.assertEqual(
                db.get_lineage(2, ancestors=True, descendants=True),
                [1, [2, "leaf_link:4", "leaf_link:5"]],
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

    def test_get_lineage_path(self):
        with FamDBRoot(TestDatabase.filenames[0], "r") as db:
            self.assertEqual(db.get_lineage_path(3), [["root", 0], ["Other Order", 0]])

            # test caching in get_lineage_path
            self.assertEqual(db.get_lineage_path(3), [["root", 0], ["Other Order", 0]])

            # test lookup without cache
            self.assertEqual(
                db.get_lineage_path(3, False), [["root", 0], ["Other Order", 0]]
            )

            # test with supplied tree
            self.assertEqual(
                db.get_lineage_path(4, [1, [2, [4]], [3]]),
                [["root", 0], ["Order", 0], ["Genus", 1]],
            )

    def test_resolve_species(self):
        with FamDBRoot(TestDatabase.filenames[0], "r") as db:
            self.assertEqual(db.resolve_species(3), [[3, 0, True]])
            self.assertEqual(db.resolve_species(4), [[4, 1, True]])
            self.assertEqual(db.resolve_species(999), [])
            self.assertEqual(db.resolve_species("Species"), [[6, 1, True]])
            self.assertEqual(db.resolve_species("Tardigrade"), [])

    def test_resolve_one_species(self):
        with FamDBRoot(TestDatabase.filenames[0], "r") as db:
            self.assertEqual(db.resolve_one_species(3), [3, 0])
            self.assertEqual(db.resolve_one_species(999), None)
            self.assertEqual(db.resolve_one_species("Species"), [6, 1])
            self.assertEqual(db.resolve_one_species("Mus musculus"), None)

    def test_get_sanitized_name(self):  # TODO add more test cases
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

    # Lineage tests --------------------------------------------------------------------------------
    def test_lineage(self):
        root_l = [1, [2, "leaf_link:4", "leaf_link:5"]]
        leaf_l = ["root_link:4", [4, [6]]]
        leaf_l2 = ["root_link:5", [5]]
        intermediate = [1, [2, [4, [6]], "leaf_link:5"]]
        final = [1, [2, [4, [6]], [5]]]
        lin_root = Lineage(root_l, True, 0)
        lin_leaf = Lineage(leaf_l, False, 1)
        lin_leaf2 = Lineage(leaf_l2, False, 2)

        # lineage can be subscripted like lists
        self.assertEqual(lin_root[1][1], "leaf_link:4")

        # init
        self.assertEqual(lin_root.root, True)
        self.assertEqual(lin_root.descendants, True)
        self.assertEqual(
            lin_root.links, {"leaf_link:": {1: "4", 3: "5"}, "root_link:": None}
        )
        self.assertEqual(lin_root.partition, 0)
        self.assertEqual(lin_leaf.descendants, False)
        self.assertEqual(lin_leaf.ancestors, True)
        self.assertEqual(
            lin_leaf.links, {"leaf_link:": {}, "root_link:": {"4": "[4, [6]]"}}
        )
        self.assertEqual(lin_leaf.partition, 1)

        # lineage can be added in any order
        self.assertEqual(lin_leaf + lin_root, intermediate)
        self.assertEqual(lin_root + lin_leaf, intermediate)

        # addion can be chained
        first = lin_root + lin_leaf
        self.assertEqual(first, intermediate)
        second = first + lin_leaf2
        self.assertEqual(second, final)

        # iadd works
        lin_root += lin_leaf
        lin_root += lin_leaf2
        self.assertEqual(lin_root, final)

    # Umbrella Methods -----------------------------------------------------------------------------
    def test_get_lineage_combined(self):
        famdb = FamDB(TestDatabase.file_dir, "r")
        # descendants from root
        self.assertEqual(
            famdb.get_lineage_combined(2, descendants=True), [2, [4, [6]], [5]]
        )
        # ancenstors from leaf
        self.assertEqual(famdb.get_lineage_combined(4, ancestors=True), [1, [2, [4]]])
        # ancestors from root
        self.assertEqual(famdb.get_lineage_combined(2, ancestors=True), [1, [2]])
        # decendants from leaf
        self.assertEqual(famdb.get_lineage_combined(4, descendants=True), [4, [6]])
        # ancestors and descendants from root
        self.assertEqual(
            famdb.get_lineage_combined(2, descendants=True, ancestors=True),
            [1, [2, [4, [6]], [5]]],
        )
        # ancestors and descendants from leaf
        self.assertEqual(
            famdb.get_lineage_combined(
                4,
                ancestors=True,
                descendants=True,
            ),
            [1, [2, [4, [6]]]],
        )

    @patch("sys.stdout", new_callable=io.StringIO)
    def test_show_files(self, mock_print):
        famdb = FamDB(TestDatabase.file_dir, "r")
        famdb.show_files()
        out = f"""\nFile Info: {TestDatabase.file_dir}
 Partition 0 Present: Root Node  
   unittest.0.h5 -> Consensi: 2, HMMs: 3

 Partition 1 Present: Search Node  
   unittest.1.h5 -> Consensi: 2, HMMs: 0

 Partition 2 Present: Other Node - Other Node 
   unittest.2.h5 -> Consensi: 1, HMMs: 0\n
"""
        self.assertEqual(mock_print.getvalue(), out)

    def test_get_lineage_path(self):
        famdb = FamDB(TestDatabase.file_dir, "r")
        self.assertEqual(
            famdb.get_lineage_path(5, ancestors=True),
            [["root", 0], ["Order", 0], ["Other Genus", 2]],
        )
        self.assertEqual(
            famdb.get_lineage_path(5, ancestors=True, partition=False, cache=False),
            ["root", "Order", "Other Genus"],
        )

    def test_get_counts(self):
        famdb = FamDB(TestDatabase.file_dir, "r")
        self.assertEqual(famdb.get_counts(), {"consensus": 5, "hmm": 3, "file": 3})

    def test_resolve_names(self):
        famdb = FamDB(TestDatabase.file_dir, "r")
        # self.assertEqual(famdb.resolve_names(4), [[4, True, 1, [['scientific name', 'Genus'], ['common name', 'Leaf Dummy 4'], 1]]])
        # self.assertEqual(famdb.resolve_names(2), [[2, True, 0, [['scientific name', 'Order'], ['common name', 'Root Dummy 2'], 0]]])
        # self.assertEqual(famdb.resolve_names("Order"), [[2, True, 0, [['scientific name', 'Order'], ['common name', 'Root Dummy 2'], 0]], [3, False, 0, [['scientific name', 'Other Order'], ['common name', 'Root Dummy 3'], 0]]])
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
                        0,
                    ],
                ]
            ],
        )
        # TODO race condition? only 3 of these will work at a time

    # test missing root file, multiple exports, different ids TODO
    # def test_FamDB_file_check(self):
    #     with self.assertRaises(SystemExit):
    #         other_file = tempfile.NamedTemporaryFile(
    #             dir="/tmp", prefix="bad", suffix=".0.h5"
    #         )
    #         famdb = FamDB(TestDatabase.file_dir, "r")
    #         other_file.close()

    # def test_FamDB_id_check(self):
    #     with self.assertRaises(SystemExit):
    #         new_info = copy.deepcopy(FILE_INFO)
    #         new_info['meta']['id'] = 'uuidNN'
    #         with FamDBRoot(TestDatabase.filenames[1], "r+") as db:
    #             db.set_file_info(new_info)
    #         famdb = FamDB('/tmp')
    #         with FamDBRoot(TestDatabase.filenames[1], "r+") as db:
    #             db.set_file_info(FILE_INFO)
