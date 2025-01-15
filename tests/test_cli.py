import os
import subprocess
import unittest
from famdb_classes import FamDB
from .doubles import init_db_file
from famdb_globals import TEST_DIR


def test_one(t, test, args):
    out_path = t.tests_dir + f"/{test}.out"
    err_path = t.tests_dir + f"/{test}.err"

    # print("Testing " + test)

    args.insert(0, os.path.join(os.path.dirname(__file__), "../famdb.py"))
    args.insert(1, "--db_dir")
    args.insert(2, TestCliOutput.file_dir)

    if os.environ.get("FAMDB_TEST_COVERAGE"):
        args.insert(0, "coverage")
        args.insert(1, "run")

    # print("running: " + str(args))
    result = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    # print("ERROR:" + str(result.stderr))
    # print("OUT:" + str(result.stdout))

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
                print("    ERROR: cli output mismatch for ", test)
            t.assertEqual(actual, expected)

    compare_output(result.stdout or "", out_path)
    compare_output(result.stderr or "", err_path)


class TestCliOutput(unittest.TestCase):
    # Set up a single database file shared by all tests in this class
    @classmethod
    def setUpClass(cls):
        file_dir = f"{TEST_DIR}/cli"
        os.makedirs(file_dir, exist_ok=True)
        db_dir = f"{file_dir}/unittest"
        init_db_file(db_dir)
        filenames = [f"{db_dir}.0.h5", f"{db_dir}.1.h5", f"{db_dir}.2.h5"]
        TestCliOutput.filenames = filenames
        TestCliOutput.file_dir = file_dir
        TestCliOutput.tests_dir = os.path.join(os.path.dirname(__file__), "cli")
        TestCliOutput.famdb = FamDB(file_dir, "r+")
        TestCliOutput.famdb.build_pruned_tree()
        TestCliOutput.famdb.close()

    @classmethod
    def tearDownClass(cls):
        filenames = TestCliOutput.filenames
        TestCliOutput.filenames = None

        for name in filenames:
            os.remove(name)
        os.rmdir(TestCliOutput.file_dir)

    # def test_families_embl_meta(self):
    #     test = "families-embl_meta"
    #     args = ["families", "--format", "embl_meta", "-d", "2"]
    #     test_one(self, test, args) TODO

    def test_families_embl_seq(self):
        test = "families-embl_seq"
        args = ["families", "--format", "embl_seq", "3"]
        test_one(self, test, args)

    # def test_families_embl(self):
    #     test = "families-embl"
    #     args = ["families", "--format", "embl", "-d", "2"]
    #     test_one(self, test, args) TODO

    def test_families_fasta_acc(self):
        test = "families-fasta_acc"
        args = [
            "families",
            "--format",
            "fasta_acc",
            "--add-reverse-complement",
            "-a",
            "4",
        ]
        test_one(self, test, args)

    def test_families_fasta_name(self):
        test = "families-fasta_name"
        args = ["families", "--format", "fasta_name", "-a", "6"]
        test_one(self, test, args)

    def test_families_hmm_speciies(self):
        test = "families-hmm_species"
        args = ["families", "--format", "hmm_species", "-ad", "3"]
        test_one(self, test, args)

    def test_families_hmm(self):
        test = "families-hmm"
        args = ["families", "--format", "hmm", "-ad", "3"]
        test_one(self, test, args)

    def test_families_summary(self):
        test = "families-summary"
        args = ["families", "-d", "1"]
        test_one(self, test, args)

    def test_family_byacc_embl(self):
        test = "family-byacc-embl"
        args = ["family", "TEST0001", "-f", "embl"]
        test_one(self, test, args)

    def test_family_byacc(self):
        test = "family-byacc"
        args = ["family", "TEST0001"]
        test_one(self, test, args)

    def test_family_byname_hmm(self):
        test = "family-byname-hmm"
        args = ["family", "TEST0003", "-f", "hmm"]
        test_one(self, test, args)

    def test_family_byname(self):
        test = "family-byname"
        args = ["family", "TEST0003", "-f", "fasta_name"]
        test_one(self, test, args)

    # def test_lineage_pretty(self):
    #     test = "lineage-pretty"
    #     args = ["lineage", "-d", "1"]
    #     test_one(self, test, args) TODO

    # def test_lineage_semicolons(self):
    #     test = "lineage-semicolon"
    #     args = ["lineage", "--format", "semicolon", "-a", "5"]
    #     test_one(self, test, args) TODO

    def test_lineage_totals(self):
        test = "lineage-totals"
        args = ["lineage", "--format", "totals", "-ad", "3"]
        test_one(self, test, args)

    def test_names_pretty(self):
        test = "names-pretty"
        args = ["names", "genus"]
        test_one(self, test, args)

    def test_names_multi_arg(self):
        test = "names-multi-arg"
        args = ["names", "other", "genus"]
        test_one(self, test, args)

    def test_names_json(self):
        test = "names-json"
        args = ["names", "--format", "json", "genus"]
        test_one(self, test, args)
