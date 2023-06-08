import unittest
import os
import shutil
import logging
from .doubles import init_single_file, make_family
from famdb_classes import FamDB


class TestExports(unittest.TestCase):
    def setUp(self):
        file_dir = "/tmp/export"
        os.makedirs(file_dir)
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
            famdb.get_db_info(),
            {
                "copyright": "<copyright header>",
                "date": "2020-07-15",
                "description": "Test Database",
                "name": "Test",
                "version": "V1",
            },
        )

    def test_add_family(self):
        init_single_file(0, self.db_dir)
        famdb = FamDB(self.file_dir, "r+")
        fam = make_family("TEST0001", [1], "ACGT", "<model1>")
        famdb.add_family(fam)
        get_fam = famdb.get_family_by_name("Test family TEST0001")
        self.assertEqual(get_fam.accession, "TEST0001")

    def test_missing_root_file(self):
        init_single_file(1, self.db_dir)
        with self.assertRaises(SystemExit):
            famdb = FamDB(self.file_dir, "r")

    def test_multiple_exports(self):
        init_single_file(0, self.db_dir)
        init_single_file(1, f"{self.file_dir}/bad")
        with self.assertRaises(SystemExit):
            famdb = FamDB(self.file_dir, "r")

    def test_different_ids(self):
        init_single_file(0, self.db_dir)
        init_single_file(1, self.db_dir, change_id=True)
        with self.assertRaises(SystemExit):
            famdb = FamDB(self.file_dir, "r")
