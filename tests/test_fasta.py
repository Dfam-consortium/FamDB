import unittest
import os

from famdb_classes import FamDBRoot
from famdb_helper_classes import Family
from .doubles import init_db_file


class TestFASTA(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        file_dir = "/tmp/fasta"
        os.makedirs(file_dir)
        db_dir = f"{file_dir}/unittest"
        init_db_file(db_dir)
        filenames = [f"{db_dir}.0.h5", f"{db_dir}.1.h5", f"{db_dir}.2.h5"]
        TestFASTA.filenames = filenames
        TestFASTA.file_dir = file_dir

    @classmethod
    def tearDownClass(cls):
        filenames = TestFASTA.filenames
        TestFASTA.filenames = None

        for name in filenames:
            os.remove(name)
        os.rmdir(TestFASTA.file_dir)

    def test_simple(self):
        fam = Family()
        fam.name = "Test1"
        fam.accession = "TEST0001"
        fam.version = 1
        fam.clades = []
        fam.consensus = "ACGTAAAA"
        with FamDBRoot(TestFASTA.filenames[0], "r") as db:
            self.assertEqual(fam.to_fasta(db), ">Test1\nACGTAAAA\n")
            self.assertEqual(
                fam.to_fasta(db, use_accession=True),
                ">TEST0001.1 name=Test1\nACGTAAAA\n",
            )

    def test_classname(self):
        fam = Family()
        fam.name = "Test2"
        fam.accession = "TEST0002"
        fam.version = 2
        fam.clades = []
        fam.consensus = "TCGATTTT"
        fam.repeat_type = "Type"
        with FamDBRoot(TestFASTA.filenames[0], "r") as db:
            self.assertEqual(
                fam.to_fasta(db, include_class_in_name=True), ">Test2#Type\nTCGATTTT\n"
            )
            fam.repeat_subtype = "SubType"
            self.assertEqual(
                fam.to_fasta(db, include_class_in_name=True),
                ">Test2#Type/SubType\nTCGATTTT\n",
            )

    def test_complement(self):
        fam = Family()
        fam.name = "Test3"
        fam.accession = "TEST0003"
        fam.version = 3
        fam.clades = []
        fam.consensus = "CGTAWWKSAAAA"
        with FamDBRoot(TestFASTA.filenames[0], "r") as db:
            self.assertEqual(
                fam.to_fasta(db, do_reverse_complement=True),
                ">Test3 (anti)\nTTTTWMSSTACG\n",
            )

    def test_clades(self):
        fam = Family()
        fam.name = "Test4"
        fam.accession = "TEST0004"
        fam.version = 4
        fam.clades = [2, 3]
        fam.consensus = "ACGT"
        with FamDBRoot(TestFASTA.filenames[0], "r") as db:
            self.assertEqual(fam.to_fasta(db), ">Test4 @Order @Other_Order\nACGT\n")

    def test_multiline(self):
        fam = Family()
        fam.name = "Test5"
        fam.accession = "TEST0005"
        fam.version = 5
        fam.clades = []
        fam.consensus = "ACGTTGCA" * 20  # 160 bp total
        with FamDBRoot(TestFASTA.filenames[0], "r") as db:
            self.assertEqual(
                fam.to_fasta(db),
                """\
>Test5
ACGTTGCAACGTTGCAACGTTGCAACGTTGCAACGTTGCAACGTTGCAACGTTGCAACGT
TGCAACGTTGCAACGTTGCAACGTTGCAACGTTGCAACGTTGCAACGTTGCAACGTTGCA
ACGTTGCAACGTTGCAACGTTGCAACGTTGCAACGTTGCA
""",
            )

    def test_buffer(self):
        fam = Family()
        fam.name = "Test6"
        fam.accession = "TEST0006"
        fam.version = 6
        fam.clades = []
        fam.consensus = "AAAAGCGCGCAAAA"
        with FamDBRoot(TestFASTA.filenames[0], "r") as db:
            self.assertEqual(
                fam.to_fasta(db, buffer=True), ">Test6#buffer\nAAAAGCGCGCAAAA\n"
            )
            self.assertEqual(
                fam.to_fasta(db, buffer=[5, 10]), ">Test6_5_10#buffer\nGCGCGC\n"
            )

    def test_all(self):
        fam = Family()
        fam.name = "Test7"
        fam.accession = "TEST0007"
        fam.version = 7
        fam.clades = [2, 3]
        fam.consensus = "ACGTTGCA" * 20  # 160 bp total
        with FamDBRoot(TestFASTA.filenames[0], "r") as db:
            self.assertEqual(
                fam.to_fasta(
                    db,
                    use_accession=True,
                    include_class_in_name=True,
                    buffer=True,
                ),
                """\
>TEST0007.7#buffer name=Test7 @Order @Other_Order
ACGTTGCAACGTTGCAACGTTGCAACGTTGCAACGTTGCAACGTTGCAACGTTGCAACGT
TGCAACGTTGCAACGTTGCAACGTTGCAACGTTGCAACGTTGCAACGTTGCAACGTTGCA
ACGTTGCAACGTTGCAACGTTGCAACGTTGCAACGTTGCA
""",
            )

        self.assertEqual(
            fam.to_fasta(
                db,
                use_accession=True,
                include_class_in_name=True,
                do_reverse_complement=True,
                buffer=[23, 39],
            ),
            """\
>TEST0007.7_23_39#buffer (anti) name=Test7 @Order @Other_Order
GCAACGTTGCAACGTTG
""",
        )

    def test_missing_consensus(self):
        fam = Family()
        fam.name = "Test8"
        fam.accession = "TEST0008"
        fam.version = 8
        fam.clades = []
        with FamDBRoot(TestFASTA.filenames[0], "r") as db:
            self.assertEqual(fam.to_fasta(db), None)

    def test_search_stages(self):
        fam = Family()
        fam.name = "Test9"
        fam.accession = "TEST0009"
        fam.version = 9
        fam.clades = [2]
        fam.consensus = "ACGT"
        fam.search_stages = "30,45"
        with FamDBRoot(TestFASTA.filenames[0], "r") as db:
            self.assertEqual(fam.to_fasta(db), ">Test9 @Order [S:30,45]\nACGT\n")

    def test_always_exports_uppercase(self):
        fam = Family()
        fam.name = "Test10"
        fam.accession = "TEST0010"
        fam.version = 10
        fam.clades = []
        fam.consensus = "acgt"
        with FamDBRoot(TestFASTA.filenames[0], "r") as db:
            self.assertEqual(fam.to_fasta(db), ">Test10\nACGT\n")

    def test_without_version(self):
        fam = Family()
        fam.accession = "Test11"
        fam.clades = []
        fam.consensus = "acgt"
        with FamDBRoot(TestFASTA.filenames[0], "r") as db:
            self.assertEqual(fam.to_fasta(db, use_accession=True), ">Test11\nACGT\n")
