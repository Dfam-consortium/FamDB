import unittest
import os

from famdb_classes import FamDBRoot
from famdb_helper_classes import Family
from .doubles import init_db_file
from famdb_globals import TEST_DIR


def test_family():
    fam = Family()
    fam.accession = "TEST0001"
    fam.title = "A Simple Test"
    fam.version = 1
    fam.clades = [4, 5]
    fam.repeat_type = "Type"
    fam.repeat_subtype = "SubType"
    fam.classification = "root;Type;SubType"
    fam.model = """\
HMMER3/f [3.1b2 | February 2015]
NAME  TEST0001#Type/SubType
LENG  100
MAXL  122
ALPH  DNA
RF    yes
MM    no
CONS  yes
CS    no
MAP   yes
DATE  Mon Aug 17 23:04:43 2015
NSEQ  2000
EFFN  18.549065
CKSUM 765031794
STATS LOCAL MSV      -10.5531  0.70202
STATS LOCAL VITERBI  -11.4974  0.70202
STATS LOCAL FORWARD   -4.5297  0.70202
HMM          A        C        G        T   
            m->m     m->i     m->d     i->m     i->i     d->m     d->d
<snip>
"""

    return fam


class TestHMM(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        file_dir = f"{TEST_DIR}/hmm"
        os.makedirs(file_dir, exist_ok=True)
        db_dir = f"{file_dir}/unittest"
        init_db_file(db_dir)
        filenames = [f"{db_dir}.0.h5", f"{db_dir}.1.h5", f"{db_dir}.2.h5"]
        TestHMM.filenames = filenames
        TestHMM.file_dir = file_dir

    @classmethod
    def tearDownClass(cls):
        filenames = TestHMM.filenames
        TestHMM.filenames = None

        for name in filenames:
            os.remove(name)
        os.rmdir(TestHMM.file_dir)

    def test_simple(self):
        fam = test_family()
        with FamDBRoot(TestHMM.filenames[0], "r") as db:
            self.assertEqual(
                fam.to_dfam_hmm(db),
                """\
HMMER3/f [3.1b2 | February 2015]
NAME  TEST0001
ACC   TEST0001.1
DESC  A Simple Test
LENG  100
MAXL  122
ALPH  DNA
RF    yes
MM    no
CONS  yes
CS    no
MAP   yes
DATE  Mon Aug 17 23:04:43 2015
NSEQ  2000
EFFN  18.549065
CKSUM 765031794
CT    Type;SubType
MS    TaxId:4 TaxName:Genus
MS    TaxId:5 TaxName:Other_Genus
CC    RepeatMasker Annotations:
CC         Type: Type
CC         SubType: SubType
CC         Species: Genus, Other_Genus
CC         SearchStages: 
CC         BufferStages: 
STATS LOCAL MSV      -10.5531  0.70202
STATS LOCAL VITERBI  -11.4974  0.70202
STATS LOCAL FORWARD   -4.5297  0.70202
HMM          A        C        G        T   
            m->m     m->i     m->d     i->m     i->i     d->m     d->d
<snip>
""",
            )

    def test_special_metadata(self):
        fam = test_family()
        fam.aliases = "Repbase:MyLTR1\nOtherDB:MyLTR\n"
        fam.refineable = True
        fam.build_method = "Example Build Method"
        fam.search_method = "Example Search Method"
        fam.description = "Example Title/Description"
        fam.general_cutoff = 25.67
        with FamDBRoot(TestHMM.filenames[0], "r") as db:

            self.assertEqual(
                fam.to_dfam_hmm(db),
                """\
HMMER3/f [3.1b2 | February 2015]
NAME  TEST0001
ACC   TEST0001.1
DESC  A Simple Test
LENG  100
MAXL  122
ALPH  DNA
RF    yes
MM    no
CONS  yes
CS    no
MAP   yes
DATE  Mon Aug 17 23:04:43 2015
NSEQ  2000
EFFN  18.549065
CKSUM 765031794
GA    25.67;
TC    25.67;
NC    25.67;
BM    Example Build Method
SM    Example Search Method
CT    Type;SubType
MS    TaxId:4 TaxName:Genus
MS    TaxId:5 TaxName:Other_Genus
CC    Example Title/Description
CC    RepeatMasker Annotations:
CC         Type: Type
CC         SubType: SubType
CC         Species: Genus, Other_Genus
CC         SearchStages: 
CC         BufferStages: 
CC         Refineable
STATS LOCAL MSV      -10.5531  0.70202
STATS LOCAL VITERBI  -11.4974  0.70202
STATS LOCAL FORWARD   -4.5297  0.70202
HMM          A        C        G        T   
            m->m     m->i     m->d     i->m     i->i     d->m     d->d
<snip>
""",
            )

    def test_species_thresholds(self):
        fam = test_family()
        fam.taxa_thresholds = "5,1.0,2.0,3.0,0.002\n3,1.0,2.0,3.0,0.002"
        with FamDBRoot(TestHMM.filenames[0], "r") as db:
            self.assertEqual(
                fam.to_dfam_hmm(db, species=4),
                """\
HMMER3/f [3.1b2 | February 2015]
NAME  TEST0001
ACC   TEST0001.1
DESC  A Simple Test
LENG  100
MAXL  122
ALPH  DNA
RF    yes
MM    no
CONS  yes
CS    no
MAP   yes
DATE  Mon Aug 17 23:04:43 2015
NSEQ  2000
EFFN  18.549065
CKSUM 765031794
TH    TaxId:5; TaxName:Other Genus; GA:1.00; TC:2.00; NC:3.00; fdr:0.002;
TH    TaxId:3; TaxName:Other Order; GA:1.00; TC:2.00; NC:3.00; fdr:0.002;
CT    Type;SubType
MS    TaxId:4 TaxName:Genus
MS    TaxId:5 TaxName:Other_Genus
CC    RepeatMasker Annotations:
CC         Type: Type
CC         SubType: SubType
CC         Species: Genus, Other_Genus
CC         SearchStages: 
CC         BufferStages: 
STATS LOCAL MSV      -10.5531  0.70202
STATS LOCAL VITERBI  -11.4974  0.70202
STATS LOCAL FORWARD   -4.5297  0.70202
HMM          A        C        G        T   
            m->m     m->i     m->d     i->m     i->i     d->m     d->d
<snip>
""",
            )

    def test_no_model(self):
        fam = test_family()
        fam.model = None
        with FamDBRoot(TestHMM.filenames[0], "r") as db:
            self.assertEqual(fam.to_dfam_hmm(db), None)

    def test_class_in_name(self):
        fam = test_family()

        with FamDBRoot(TestHMM.filenames[0], "r") as db:
            self.assertEqual(
                fam.to_dfam_hmm(db, include_class_in_name=True),
                """\
HMMER3/f [3.1b2 | February 2015]
NAME  TEST0001#Type/SubType
ACC   TEST0001.1
DESC  A Simple Test
LENG  100
MAXL  122
ALPH  DNA
RF    yes
MM    no
CONS  yes
CS    no
MAP   yes
DATE  Mon Aug 17 23:04:43 2015
NSEQ  2000
EFFN  18.549065
CKSUM 765031794
CT    Type;SubType
MS    TaxId:4 TaxName:Genus
MS    TaxId:5 TaxName:Other_Genus
CC    RepeatMasker Annotations:
CC         Type: Type
CC         SubType: SubType
CC         Species: Genus, Other_Genus
CC         SearchStages: 
CC         BufferStages: 
STATS LOCAL MSV      -10.5531  0.70202
STATS LOCAL VITERBI  -11.4974  0.70202
STATS LOCAL FORWARD   -4.5297  0.70202
HMM          A        C        G        T   
            m->m     m->i     m->d     i->m     i->i     d->m     d->d
<snip>
""",
            )
