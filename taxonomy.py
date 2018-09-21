# -*- coding: utf-8 -*-
"""
    taxonomy.py

    TaxNode class and related functions for working with the NCBI
    taxonomy database dumps.

SEE ALSO:
    Dfam: http://www.dfam.org

AUTHOR(S):
    Jeb Rosen <jeb.rosen@systemsbiology.org>

LICENSE:
    This code may be used in accordance with the Creative Commons
    Zero ("CC0") public domain dedication:
    https://creativecommons.org/publicdomain/zero/1.0/

DISCLAIMER:
    This software is provided ``AS IS'' and any express or implied
    warranties, including, but not limited to, the implied warranties of
    merchantability and fitness for a particular purpose, are disclaimed.
    In no event shall the authors or the Dfam consortium members be
    liable for any direct, indirect, incidental, special, exemplary, or
    consequential damages (including, but not limited to, procurement of
    substitute goods or services; loss of use, data, or profits; or
    business interruption) however caused and on any theory of liability,
    whether in contract, strict liability, or tort (including negligence
    or otherwise) arising in any way out of the use of this software, even
    if advised of the possibility of such damage.
"""

import logging

LOGGER = logging.getLogger(__name__)


class TaxNode:  # pylint: disable=too-few-public-methods
    """An NCBI Taxonomy node linked to its parent and children."""
    def __init__(self, tax_id, parent_id):
        self.tax_id = tax_id
        self.parent_id = parent_id
        self.names = []

        self.parent_node = None
        self.families = []
        self.children = []
        self.used = False

    def mark_ancestry_used(self):
        """Marks 'self' and all of its ancestors as 'used', up until the first 'used' ancestor."""
        node = self
        while node is not None:
            if node.used:
                break
            node.used = True
            node = node.parent_node


def read_taxdb(directory):
    """Reads NCBI Taxonomy data from 'directory' and returns it as a dict."""

    nodes = {}

    LOGGER.info("Reading taxonomy nodes (nodes.dmp)")
    with open(directory + "/nodes.dmp") as nodes_file:
        for line in nodes_file:
            fields = line.split("|")
            tax_id = int(fields[0])
            parent_id = int(fields[1])
            nodes[tax_id] = TaxNode(tax_id, parent_id)

    for node in nodes.values():
        if node.tax_id != 1:
            node.parent_node = nodes[node.parent_id]
            node.parent_node.children += [node]

    LOGGER.info("Reading taxonomy names (names.dmp)")
    with open(directory + "/names.dmp") as names_file:
        for line in names_file:
            fields = line.split("|")
            tax_id = int(fields[0])
            name_txt = fields[1].strip()
            name_class = fields[3].strip()
            nodes[tax_id].names += [[name_class, name_txt]]

    LOGGER.info("Loaded %d taxonomy nodes", len(nodes))

    return nodes
