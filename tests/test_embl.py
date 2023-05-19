import json
import unittest
import os

from famdb_classes import FamDB
from famdb_helper_classes import Family, Lineage
from .doubles import init_db_file


class TestEMBL(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        filenames = ["/tmp/unittest.0.h5", "/tmp/unittest.1.h5", "/tmp/unittest.2.h5"]
        init_db_file("/tmp/unittest")
        TestEMBL.filenames = filenames
        cls.maxDiff = None

    @classmethod
    def tearDownClass(cls):
        filenames = TestEMBL.filenames
        TestEMBL.filenames = None

        for name in filenames:
            os.remove(name)

    def test_simple(self):
        fam = Family()
        fam.name = "Test1"
        fam.accession = "TEST0001"
        fam.version = 1
        fam.clades = [4]
        fam.consensus = "ACGTAAAA"
        fam.repeat_type = "Type"
        fam.repeat_subtype = "SubType"

        famdb = FamDB("/tmp")
        self.assertEqual(
            fam.to_embl(famdb),
            """\
ID   TEST0001; SV 1; linear; DNA; STD; UNC; 8 BP.
NM   Test1
XX
AC   TEST0001;
XX
XX
KW   Type/SubType.
XX
OS   Genus
OC   .
XX
CC
CC   RepeatMasker Annotations:
CC        Type: Type
CC        SubType: SubType
CC        Species: Genus
CC        SearchStages: 
CC        BufferStages: 
XX
SQ   Sequence 8 BP; 5 A; 1 C; 1 G; 1 T; 0 other;
     acgtaaaa                                                           8
//
""",
        )

    def test_multiline(self):
        fam = Family()
        fam.name = "Test2"
        fam.accession = "TEST0002"
        fam.version = 2
        fam.clades = [5]
        fam.consensus = "ACGTTGCA" * 20  # 160 bp total
        fam.repeat_type = "Test"
        fam.repeat_subtype = "Multiline"

        famdb = FamDB("/tmp")
        self.assertEqual(
            fam.to_embl(famdb),
            """\
ID   TEST0002; SV 2; linear; DNA; STD; UNC; 160 BP.
NM   Test2
XX
AC   TEST0002;
XX
XX
KW   Test/Multiline.
XX
OS   Other Genus
OC   .
XX
CC
CC   RepeatMasker Annotations:
CC        Type: Test
CC        SubType: Multiline
CC        Species: Other_Genus
CC        SearchStages: 
CC        BufferStages: 
XX
SQ   Sequence 160 BP; 40 A; 40 C; 40 G; 40 T; 0 other;
     acgttgcaac gttgcaacgt tgcaacgttg caacgttgca acgttgcaac gttgcaacgt  60
     tgcaacgttg caacgttgca acgttgcaac gttgcaacgt tgcaacgttg caacgttgca  120
     acgttgcaac gttgcaacgt tgcaacgttg caacgttgca                        160
//
""",
        )

    def test_metaonly(self):
        fam = Family()
        fam.name = "Test3"
        fam.accession = "TEST0003"
        fam.version = 3
        fam.clades = [5]
        fam.consensus = "ACGTTGCA"
        fam.repeat_type = "Test"
        fam.repeat_subtype = "Metadata"

        famdb = FamDB("/tmp")
        self.assertEqual(
            fam.to_embl(famdb, include_seq=False),
            """\
ID   TEST0003; SV 3; linear; DNA; STD; UNC; 8 BP.
NM   Test3
XX
AC   TEST0003;
XX
XX
KW   Test/Metadata.
XX
OS   Other Genus
OC   .
XX
CC
CC   RepeatMasker Annotations:
CC        Type: Test
CC        SubType: Metadata
CC        Species: Other_Genus
CC        SearchStages: 
CC        BufferStages: 
XX
//
""",
        )

    def test_seqonly(self):
        fam = Family()
        fam.name = "Test4"
        fam.accession = "TEST0004"
        fam.version = 4
        fam.clades = [5]
        fam.consensus = "ACGTTGCA"
        fam.repeat_type = "Test"
        fam.repeat_subtype = "SequenceOnly"

        famdb = FamDB("/tmp")
        self.assertEqual(
            fam.to_embl(famdb, include_meta=False),
            """\
ID   TEST0004; SV 4; linear; DNA; STD; UNC; 8 BP.
NM   Test4
XX
AC   TEST0004;
XX
XX
SQ   Sequence 8 BP; 2 A; 2 C; 2 G; 2 T; 0 other;
     acgttgca                                                           8
//
""",
        )

    def test_special_metadata(self):
        fam = Family()
        fam.name = "Test5"
        fam.accession = "TEST0005"
        fam.version = 5
        fam.clades = [5, 3]
        fam.consensus = "ACGTTGCAGAGAKWCTCT"
        fam.repeat_type = "LTR"
        fam.repeat_subtype = "BigTest"
        fam.aliases = "Repbase:MyLTR1\nOtherDB:MyLTR\n"
        fam.refineable = True

        famdb = FamDB("/tmp")
        self.assertEqual(
            fam.to_embl(famdb),
            """\
ID   TEST0005; SV 5; linear; DNA; STD; UNC; 18 BP.
NM   Test5
XX
AC   TEST0005;
XX
XX
DR   Repbase; MyLTR1.
XX
KW   Long terminal repeat of retrovirus-like element; Test5.
XX
OS   Other Genus
OC   .
OS   Other Order
OC   .
XX
CC
CC   RepeatMasker Annotations:
CC        Type: LTR
CC        SubType: BigTest
CC        Species: Other_Genus, Other_Order
CC        SearchStages: 
CC        BufferStages: 
CC        Refineable
XX
SQ   Sequence 18 BP; 4 A; 4 C; 4 G; 4 T; 2 other;
     acgttgcaga gakwctct                                                18
//
""",
        )

    def test_attached_to_root(self):
        fam = Family()
        fam.name = "Test6"
        fam.accession = "TEST0006"
        fam.version = 6
        fam.clades = [1]
        fam.consensus = "ACGTTGCAGAGACTCT"
        fam.repeat_type = "Test"
        fam.repeat_subtype = "RootTaxa"

        famdb = FamDB("/tmp")
        self.assertEqual(
            fam.to_embl(famdb, include_seq=False),
            """\
ID   TEST0006; SV 6; linear; DNA; STD; UNC; 16 BP.
NM   Test6
XX
AC   TEST0006;
XX
XX
KW   Test/RootTaxa.
XX
OS   root
OC   .
XX
CC
CC   RepeatMasker Annotations:
CC        Type: Test
CC        SubType: RootTaxa
CC        Species: root
CC        SearchStages: 
CC        BufferStages: 
XX
//
""",
        )

    def test_citations(self):
        fam = Family()
        fam.name = "Test7"
        fam.accession = "TEST0007"
        fam.version = 7
        fam.clades = [2]
        fam.consensus = "ACGTTGCAGAGACTCT"
        fam.length = 16
        fam.repeat_type = "Test"
        fam.repeat_subtype = "HasCitations"
        fam.citations = json.dumps(
            [
                {
                    "order_added": 1,
                    "authors": "John Doe",
                    "title": "Testing Citation Export Formatting",
                    "journal": "Unit Tests 7(2), 2020.",
                },
                {
                    "order_added": 2,
                    "authors": "Jane Doe",
                    "title": "Testing Citation Export Formatting",
                    "journal": "Unit Tests 7(2), 2020.",
                },
            ]
        )

        famdb = FamDB("/tmp")
        self.assertEqual(
            fam.to_embl(famdb, include_seq=False),
            """\
ID   TEST0007; SV 7; linear; DNA; STD; UNC; 16 BP.
NM   Test7
XX
AC   TEST0007;
XX
XX
KW   Test/HasCitations.
XX
OS   Order
OC   .
XX
RN   [1] (bases 1 to 16)
RA   John Doe
RT   Testing Citation Export Formatting
RL   Unit Tests 7(2), 2020.
XX
RN   [2] (bases 1 to 16)
RA   Jane Doe
RT   Testing Citation Export Formatting
RL   Unit Tests 7(2), 2020.
XX
CC
CC   RepeatMasker Annotations:
CC        Type: Test
CC        SubType: HasCitations
CC        Species: Order
CC        SearchStages: 
CC        BufferStages: 
XX
//
""",
        )

    def test_cds(self):
        fam = Family()
        fam.name = "Test8"
        fam.accession = "TEST0008"
        fam.version = 8
        fam.clades = [2]
        fam.consensus = "ACGTTGCAGAGACTCT"
        fam.repeat_type = "Test"
        fam.repeat_subtype = "CodingSequence"
        fam.coding_sequences = json.dumps(
            [
                {
                    "cds_start": 1,
                    "cds_end": 6,
                    "product": "FAKE",
                    "exon_count": 1,
                    "description": "Example coding sequence",
                    "translation": "TL",
                },
                {
                    "cds_start": 5,
                    "cds_end": 16,
                    "product": "FAKE2",
                    "exon_count": 1,
                    "description": "Another example coding sequence",
                    "translation": "CRDS",
                },
            ]
        )
        famdb = FamDB("/tmp")
        self.assertEqual(
            fam.to_embl(famdb, include_seq=False),
            """\
ID   TEST0008; SV 8; linear; DNA; STD; UNC; 16 BP.
NM   Test8
XX
AC   TEST0008;
XX
XX
KW   Test/CodingSequence.
XX
OS   Order
OC   .
XX
CC
CC   RepeatMasker Annotations:
CC        Type: Test
CC        SubType: CodingSequence
CC        Species: Order
CC        SearchStages: 
CC        BufferStages: 
XX
FH   Key             Location/Qualifiers
FH
FT   CDS             1..6
FT                   /product="FAKE"
FT                   /number=1
FT                   /note="Example coding sequence"
FT                   /translation="TL"
FT   CDS             5..16
FT                   /product="FAKE2"
FT                   /number=1
FT                   /note="Another example coding sequence"
FT                   /translation="CRDS"
XX
//
""",
        )


def test_no_consensus(self):
    fam = Family()
    fam.name = "Test9"
    fam.accession = "TEST0009"
    fam.version = 9
    fam.clades = [2]

    self.assertEqual(fam.to_embl(None), None)
