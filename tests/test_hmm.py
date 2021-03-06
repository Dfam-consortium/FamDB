import json
import unittest

from famdb import Family
from .doubles import fakedb

def test_family():
    fam = Family()
    fam.accession = "TEST0001"
    fam.title = "A Simple Test"
    fam.version = 1
    fam.clades = [5, 3]
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
    def setUp(self):
        self.maxDiff = None

    def test_simple(self):
        fam = test_family()

        self.assertEqual(
            fam.to_dfam_hmm(fakedb()),
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
MS    TaxId:5 TaxName:Species_1
MS    TaxId:3 TaxName:Another_Clade_3.
CC    RepeatMasker Annotations:
CC         Type: Type
CC         SubType: SubType
CC         Species: Species_1, Another_Clade_3.
CC         SearchStages: 
CC         BufferStages: 
STATS LOCAL MSV      -10.5531  0.70202
STATS LOCAL VITERBI  -11.4974  0.70202
STATS LOCAL FORWARD   -4.5297  0.70202
HMM          A        C        G        T   
            m->m     m->i     m->d     i->m     i->i     d->m     d->d
<snip>
"""
        )

    def test_special_metadata(self):
        fam = test_family()
        fam.aliases = "Repbase:MyLTR1\nOtherDB:MyLTR\n"
        fam.refineable = True
        fam.build_method = "Example Build Method"
        fam.search_method = "Example Search Method"
        fam.description = "Example Title/Description"
        fam.general_cutoff = 25.67

        self.assertEqual(
            fam.to_dfam_hmm(fakedb()),
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
MS    TaxId:5 TaxName:Species_1
MS    TaxId:3 TaxName:Another_Clade_3.
CC    Example Title/Description
CC    RepeatMasker Annotations:
CC         Type: Type
CC         SubType: SubType
CC         Species: Species_1, Another_Clade_3.
CC         SearchStages: 
CC         BufferStages: 
CC         Refineable
STATS LOCAL MSV      -10.5531  0.70202
STATS LOCAL VITERBI  -11.4974  0.70202
STATS LOCAL FORWARD   -4.5297  0.70202
HMM          A        C        G        T   
            m->m     m->i     m->d     i->m     i->i     d->m     d->d
<snip>
"""
        )

    def test_no_model(self):
        fam = test_family()
        fam.model = None
        self.assertEqual(fam.to_dfam_hmm(None), None)

    def test_species_thresholds(self):
        fam = test_family()
        fam.taxa_thresholds = "5,1.0,2.0,3.0,0.002\n3,1.0,2.0,3.0,0.002"

        self.assertEqual(
            fam.to_dfam_hmm(fakedb(), species=3),
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
GA    1.00;
TC    2.00;
NC    3.00;
TH    TaxId:5; TaxName:Species 1; GA:1.00; TC:2.00; NC:3.00; fdr:0.002;
TH    TaxId:3; TaxName:Another Clade (3.); GA:1.00; TC:2.00; NC:3.00; fdr:0.002;
CT    Type;SubType
MS    TaxId:5 TaxName:Species_1
MS    TaxId:3 TaxName:Another_Clade_3.
CC    RepeatMasker Annotations:
CC         Type: Type
CC         SubType: SubType
CC         Species: Species_1, Another_Clade_3.
CC         SearchStages: 
CC         BufferStages: 
STATS LOCAL MSV      -10.5531  0.70202
STATS LOCAL VITERBI  -11.4974  0.70202
STATS LOCAL FORWARD   -4.5297  0.70202
HMM          A        C        G        T   
            m->m     m->i     m->d     i->m     i->i     d->m     d->d
<snip>
"""
        )

    def test_class_in_name(self):
        fam = test_family()

        self.assertEqual(
            fam.to_dfam_hmm(fakedb(), include_class_in_name=True),
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
MS    TaxId:5 TaxName:Species_1
MS    TaxId:3 TaxName:Another_Clade_3.
CC    RepeatMasker Annotations:
CC         Type: Type
CC         SubType: SubType
CC         Species: Species_1, Another_Clade_3.
CC         SearchStages: 
CC         BufferStages: 
STATS LOCAL MSV      -10.5531  0.70202
STATS LOCAL VITERBI  -11.4974  0.70202
STATS LOCAL FORWARD   -4.5297  0.70202
HMM          A        C        G        T   
            m->m     m->i     m->d     i->m     i->i     d->m     d->d
<snip>
"""
        )

