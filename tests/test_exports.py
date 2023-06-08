import unittest
import os
import shutil
import unittest.mock
from .doubles import init_single_file
from famdb_classes import FamDB


class TestExports(unittest.TestCase):
    def setUp(self):
        file_dir = "/tmp/export"
        os.makedirs(file_dir)
        db_dir = f"{file_dir}/unittest"
        self.file_dir = file_dir
        self.db_dir = db_dir

        self.maxDiff = None

    def tearDown(self):
        shutil.rmtree(self.file_dir)

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
        pass

    def test_missing_root_file(self):
        pass

    def test_multiple_exports(self):
        pass

    def test_different_ids(self):
        pass
