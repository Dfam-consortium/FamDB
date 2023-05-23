import os
import subprocess
import tempfile
import unittest

from .doubles import init_db_file
from famdb_classes import FamDB


def test_one(t, filename, spec_path):
    out_path = spec_path.replace(".args", ".out")
    err_path = spec_path.replace(".args", ".err")

    print("Testing " + spec_path)

    with open(spec_path) as infile:
        args = [line.rstrip("\r\n") for line in infile]

    args.insert(0, os.path.join(os.path.dirname(__file__), "../famdb.py"))
    if len(args) > 1:
        args.insert(1, "--file")
        args.insert(2, filename)

    if os.environ.get("FAMDB_TEST_COVERAGE"):
        args.insert(0, "coverage")
        args.insert(1, "run")

    print("running: " + str(args))
    result = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    print("ERROR:" + str(result.stderr))
    print("OUT:" + str(result.stdout))

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

            if actual != expected:
                print("    ERROR: cli output mismatch for ", spec_path)
            t.assertEqual(actual, expected)

    compare_output(result.stdout or "", out_path)
    compare_output(result.stderr or "", err_path)


class TestCliOutput(unittest.TestCase):
    # Set up a single database file shared by all tests in this class
    @classmethod
    def setUpClass(cls):
        file_dir = "/tmp/cli"
        os.makedirs(file_dir)
        db_dir = f"{file_dir}/unittest"
        init_db_file(db_dir)
        filenames = [f"{db_dir}.0.h5", f"{db_dir}.1.h5", f"{db_dir}.2.h5"]
        TestCliOutput.filenames = filenames
        TestCliOutput.file_dir = file_dir
        # TestCliOutput.tests_dir = os.path.join(os.path.dirname(__file__), "cli")

    @classmethod
    def tearDownClass(cls):
        filenames = TestCliOutput.filenames
        TestCliOutput.filenames = None

        for name in filenames:
            os.remove(name)
        os.rmdir(TestCliOutput.file_dir)

    def test_dummy(self):
        pass
    
    # def test_no_args(self):
    #     test = 'no-args'
    #     cli = self.tests_dir + f'/{test}.args'
    #     famdb = FamDB('/tmp', 'r')
    #     test_one(self, famdb, cli)
