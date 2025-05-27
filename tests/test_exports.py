import unittest
import os
import shutil
import logging
from .doubles import init_single_file, make_family
from famdb_classes import FamDB
from famdb_globals import FAMDB_VERSION, TEST_DIR, DESCRIPTION


class TestExports(unittest.TestCase):
    def setUp(self):
        file_dir = f"{TEST_DIR}/export"
        os.makedirs(file_dir, exist_ok=True)
        db_dir = f"{file_dir}/unittest"
        self.file_dir = file_dir
        self.db_dir = db_dir
        logging.disable(logging.CRITICAL)

    def tearDown(self):
        shutil.rmtree(self.file_dir)
        logging.disable(logging.NOTSET)

    def test_export(self):
        init_single_file(0, self.db_dir)
        famdb = FamDB(self.file_dir, "r")
        self.assertEqual(
            famdb.get_metadata(),
            {
                "copyright": "<copyright header>",
                "date": "2020-07-15",
                "description": DESCRIPTION,
                "name": "Test Dfam",
                "db_version": "V1",
                "famdb_version": FAMDB_VERSION,
                "created": "<creation date>",
                "partition_name": "Root Node",
                "partition_detail": "",
            },
        )

    def test_add_family(self):
        init_single_file(0, self.db_dir)
        famdb = FamDB(self.file_dir, "r+")
        fam = make_family("TEST0001", [1], "ACGT", "<model1>")
        famdb.files[0].add_family(fam)
        get_fam = famdb.get_family_by_name("Test family TEST0001")
        self.assertEqual(get_fam.accession, "TEST0001")

    def test_add_family_duplicate(self):
        init_single_file(0, self.db_dir)
        famdb = FamDB(self.file_dir, "r+")
        fam = make_family("TEST0001", [1], "ACGT", "<model1>")
        famdb.files[0].add_family(fam)
        # check duplicate accessions and names
        fam_dup_acc = make_family("TEST0001", [1], "TGCA", "<model2>")
        self.assertRaises(Exception, famdb.files[0].add_family, fam_dup_acc)
        # check different accessions with same name
        fam_dup_name = make_family("TEST0001", [1], "TGCA", "<model2>")
        fam_dup_name.accession = "TestAcc"
        self.assertRaises(Exception, famdb.files[0].add_family, fam_dup_name)
        # check same accessions with missing name
        fam_dup_no_name = make_family("TEST0001", [1], "TGCA", "<model2>")
        fam_dup_no_name.name = None
        self.assertRaises(Exception, famdb.files[0].add_family, fam_dup_no_name)

    def test_missing_root_file(self):
        init_single_file(1, self.db_dir)
        with self.assertRaises(SystemExit):
            famdb = FamDB(self.file_dir, "r")

    def test_multiple_roots(self):
        init_single_file(0, self.db_dir)
        init_single_file(0, f"{self.file_dir}/bad")
        with self.assertRaises(SystemExit):
            famdb = FamDB(self.file_dir, "r")

    def test_multiple_exports(self):
        init_single_file(0, self.db_dir)
        init_single_file(1, f"{self.db_dir}-bad")
        with self.assertRaises(SystemExit):
            famdb = FamDB(self.file_dir, "r")

    def test_different_ids(self):
        init_single_file(0, self.db_dir)
        init_single_file(1, self.db_dir, change_id=True)
        with self.assertRaises(SystemExit):
            famdb = FamDB(self.file_dir, "r")


#     # def test_fasta_all(self):
#     #     pass TODO
