import os
import subprocess
import tempfile
import unittest

from .doubles import init_db_file

def test_one(t, filename, spec_path):
    out_path = spec_path.replace(".args", ".out")
    err_path = spec_path.replace(".args", ".err")

    print("Testing " + spec_path)

    with open(spec_path) as infile:
        args = [line.rstrip("\r\n") for line in infile]

    args.insert(0, os.path.join(os.path.dirname(__file__), "../famdb.py"))
    args.insert(1, "--file")
    args.insert(2, filename)

    if os.environ.get("FAMDB_TEST_COVERAGE"):
        args.insert(0, "coverage")
        args.insert(1, "run")

    result = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def compare_output(actual, expected_file):
        if os.environ.get("FAMDB_TEST_BLESS"):
            if actual:
                with open(expected_file, "wb") as expfile:
                    expfile.write(actual)
            else:
                if os.path.exists(expected_file):
                    os.remove(expected_file)
        else:
            try:
                with open(expected_file, "rb") as expfile:
                    expected = expfile.read()
            except FileNotFoundError:
                expected = ""
            t.assertEqual(actual, expected)

    compare_output(result.stdout or "", out_path)
    compare_output(result.stderr or "", err_path)


class TestCliOutput(unittest.TestCase):
    def setUp(self):
        self.maxDiff = None

    # Set up a single database file shared by all tests in this class
    @classmethod
    def setUpClass(cls):
        filename = "/tmp/famdbtestfile.h5"
        init_db_file(filename)
        TestCliOutput.filename = filename

    @classmethod
    def tearDownClass(cls):
        filename = TestCliOutput.filename
        TestCliOutput.filename = None

        os.remove(filename)

    def test_cli_output(self):
        tests_dir = os.path.join(os.path.dirname(__file__), "cli")

        with os.scandir(tests_dir) as entries:
            for entry in entries:
                if entry.is_file() and entry.name.endswith(".args"):
                    test_one(self, self.filename, entry.path)
