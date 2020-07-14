import famdb

# A "mock" FamDB that can only answer some taxonomy queries.
# Should be kept in sync with FamDB as necessary.
class MockFamDB:
    def __init__(self, names_dump):
        self.names_dump = names_dump

    def get_taxon_name(self, tax_id, kind='scientific name'):
        names = self.names_dump[str(tax_id)]
        for name in names:
            if name[0] == kind:
                return name[1]

        return None

    def get_sanitized_name(self, tax_id):
        name = self.get_taxon_name(tax_id, 'scientific name')
        if name:
            name = famdb.sanitize_name(name)
        return name

# Returns a particular set of mocked clades
def mockdb():
    return MockFamDB({
        "2": [["scientific name", "A Clade"]],
        "3": [["scientific name", "Another Clade (3.)"]],
    })


