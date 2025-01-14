import unittest
import os
import shutil
import logging
from .doubles import init_single_file, make_family
from famdb_classes import FamDB
from famdb_globals import FILE_VERSION, GENERATOR_VERSION, TEST_DIR


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
                "description": "Test Database",
                "name": "Test",
                "db_version": "V1",
                "generator": GENERATOR_VERSION,
                "famdb_version": FILE_VERSION,
                "created": "2023-01-09 09:57:56.026443",
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

    def test_missing_root_file(self):
        init_single_file(1, self.db_dir)
        with self.assertRaises(SystemExit):
            famdb = FamDB(self.file_dir, "r")

    def test_multiple_roots(self):
        init_single_file(0, self.db_dir)
        init_single_file(0, f"{self.file_dir}/bad")
        with self.assertRaises(SystemExit):
            famdb = FamDB(self.file_dir, "r")

    # def test_multiple_exports(self):
    #     init_single_file(0, self.db_dir)
    #     init_single_file(1, f"{self.db_dir}-bad")
    #     with self.assertRaises(SystemExit):
    #         famdb = FamDB(self.file_dir, "r")

    def test_different_ids(self):
        init_single_file(0, self.db_dir)
        init_single_file(1, self.db_dir, change_id=True)
        with self.assertRaises(SystemExit):
            famdb = FamDB(self.file_dir, "r")


#     # def test_fasta_all(self):
#     #     pass TODO
