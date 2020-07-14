import famdb

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


