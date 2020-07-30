import famdb

# lightweight taxonomy node suitable for MockFamDB
class Node:
    def __init__(self, id, parent):
        self.id = id
        self.parent = parent
        self.children = []

# A "mock" FamDB that overrides some methods with fake data.
# Should be kept in sync with FamDB as necessary.
class MockFamDB(famdb.FamDB):
    def __init__(self, names_dump, tree):
        self.names_dump = names_dump
        self.taxa = {}

        def objectize(tree, parent, into):
            id = tree[0]
            node = Node(id, parent)
            for subtree in tree[1:]:
                node.children.append(objectize(subtree, node, into))

            into[tree[0]] = node
            return node

        objectize(tree, None, self.taxa)

        # TODO: ugly
        self._FamDB__lineage_cache = {}

    def get_lineage(self, tax_id, **kwargs):
        if kwargs.get("descendants"):
            def descendants_of(node):
                descendants = [node.id]
                for child in node.children:
                    descendants += [descendants_of(child)]
                return descendants
            tree = descendants_of(self.taxa[tax_id])
        else:
            tree = [tax_id]

        if kwargs.get("ancestors"):
            while tax_id:
                node = self.taxa[tax_id]
                if node.parent is not None:
                    tax_id = node.parent.id
                    tree = [tax_id, tree]
                else:
                    tax_id = None

        return tree

# Returns a particular set of mocked clades
def mockdb():
    return MockFamDB({
        "1": [["scientific name", "root"]],
        "2": [["scientific name", "A Clade"]],
        "3": [["scientific name", "Another Clade (3.)"]],
        "4": [["scientific name", "Parent Clade"]],
        "5": [["scientific name", "Species 1"]],
    }, [1, [4, [2, [5]]], [3]])

# taxonomy node with the minimum properties required by FamDB
class MockTaxNode:
    def __init__(self, tax_id, parent, sci_name):
        self.tax_id = tax_id
        if parent is None:
            self.parent_id = None
        else:
            self.parent_id = parent.tax_id
        self.names = [["scientific name", sci_name]]

        self.parent_node = parent
        self.children = []
        self.used = True

        if parent:
            parent.children.append(self)

# convenience function to generate a test family
def make_family(acc, clades, consensus, model):
    fam = famdb.Family()
    fam.accession = acc
    fam.name = "Test family " + acc
    fam.version = 1
    fam.clades = clades
    fam.consensus = consensus
    fam.model = model

    return fam

def init_db_file(filename):
    with famdb.FamDB(filename, "w") as db:
        db.set_db_info("Test", "V1", "2020-07-15", "Test Database", "<copyright header>")

        families = [
            make_family("TEST0001", [1], "ACGT", "<model1>"),
            make_family("TEST0002", [2, 3], None, "<model2>"),
            make_family("TEST0003", [3], "GGTC", "<model3>"),
            make_family("TEST0004", [2], "CCCCTTTT", None),
            make_family("DR0000001", [6], "GCATATCG", None),
            make_family("DR_Repeat1", [5], "CGACTAT", None),
        ]

        families[1].name = None
        families[2].search_stages = "30,40"
        families[3].buffer_stages = "10[1-2],10[5-8],20"
        families[3].search_stages = "35"
        families[3].repeat_type = "SINE"

        for fam in families:
            db.add_family(fam)

        taxa = {}
        taxa[1] = MockTaxNode(1, None, "root")
        taxa[2] = MockTaxNode(2, taxa[1], "Clade 2")
        taxa[3] = MockTaxNode(3, taxa[1], "Third Clade")
        taxa[4] = MockTaxNode(4, taxa[3], "Unused Clade")
        taxa[4].used = False
        taxa[5] = MockTaxNode(5, taxa[3], "Drosophila <flies>")
        taxa[6] = MockTaxNode(6, taxa[3], "Drosophila <fungus>")

        db.write_taxonomy(taxa)
        db.finalize()
