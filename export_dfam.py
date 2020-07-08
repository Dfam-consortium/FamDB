#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
    Export the dfam database to FamDB format.

    Usage: export_dfam.py [-h] [-l LOG_LEVEL] [-t tax_id] [-t tax_id]... [-r] connection_string outfile

    -t, --taxon: Additional taxonomy IDs to include, even if they appear
                 to be unnecessary
    -r, --raw  : Include raw families (DR*) records, not only DF* (the default)

SEE ALSO:
    famdb.py
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

import argparse
import gzip
import itertools
import json
import logging
import re
import time

import sqlalchemy
from sqlalchemy import bindparam
from sqlalchemy.ext import baked

import dfam_31 as dfam
import famdb

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
        self.ancestral = 0

    def mark_ancestry_used(self):
        """Marks 'self' and all of its ancestors as 'used', up until the first 'used' ancestor."""
        node = self
        while node is not None:
            if node.used:
                break
            node.used = True
            node = node.parent_node

    def add_ancestral_total(self, count):
        """Add 'count' to the value of 'ancestral' for 'self' and all descendants"""
        self.ancestral += count
        for child in self.children:
            child.add_ancestral_total(count)

    def mark_descendants_used(self):
        """Marks 'self' and all of its descendants as 'used'."""
        self.used = True
        for child in self.children:
            child.mark_descendants_used()


def famdb_file_type(mode):
    """Returns a type suitable for use with argparse, opening a FamDB file when active."""
    return lambda filename: famdb.FamDB(filename, mode)


def load_taxonomy(session):
    """Loads all taxonomy nodes from the database."""
    nodes = {}

    LOGGER.info("Reading taxonomy nodes")
    start = time.perf_counter()

    for tax_node in session.query(
            dfam.NcbiTaxdbNode.tax_id,
            dfam.NcbiTaxdbNode.parent_id
        ).all():
        nodes[tax_node.tax_id] = TaxNode(tax_node.tax_id, tax_node.parent_id)

    for node in nodes.values():
        if node.tax_id != 1:
            node.parent_node = nodes[node.parent_id]
            node.parent_node.children += [node]

    delta = time.perf_counter() - start
    LOGGER.info("Loaded %d taxonomy nodes in %f seconds", len(nodes), delta)

    return nodes


def load_taxonomy_names(nodes, session):
    """
    Loads the names of all taxonomy nodes in the database into 'nodes'.
    Returns a reverse lookup of sanitized name to ID
        (primarily for reading species names in existing EMBL files).
    """

    LOGGER.info("Reading taxonomy names")
    start = time.perf_counter()

    lookup = {}

    # Load *all* names. As the number of included names grows large this
    # is actually faster than loading only the needed ones from the
    # database, at the cost of memory usage
    for entry in session.query(
            dfam.NcbiTaxdbName.tax_id,
            dfam.NcbiTaxdbName.name_txt,
            dfam.NcbiTaxdbName.unique_name,
            dfam.NcbiTaxdbName.name_class,
    ):
        name = entry.unique_name or entry.name_txt
        nodes[entry.tax_id].names += [[entry.name_class, name]]
        if entry.name_class == "scientific name":
            sanitized_name = famdb.sanitize_name(name).lower()
            lookup[sanitized_name] = entry.tax_id

    delta = time.perf_counter() - start
    LOGGER.info("Loaded taxonomy names in %f", delta)

    return lookup


def calculate_ancestral_totals(nodes):
    """Calculates the count of 'ancestral' entries for all nodes."""
    for node in nodes.values():
        count = len(node.families)
        node.add_ancestral_total(count)


def mark_used_threshold(nodes, thresh):
    """Marks as used all nodes with at least 'thresh' ancestral families."""
    for node in nodes.values():
        if node.ancestral >= thresh:
            node.mark_descendants_used()


def count_extra_taxa(nodes, lookup, filename):
    """
    Counts species assignments from the "Species:" lines of a
    RepeatMasker-formatted EMBL file, to ensure that the necessary taxa are
    included in the famdb file ahead of time to support merging and queries for
    that dataset.
    """
    with open(filename) as embl_file:
        for line in embl_file:
            fields = line.lower().split(maxsplit=2)
            if len(fields) > 2:
                names = fields[2].split(",")
                for name in names:
                    name = name.strip()
                    tax_id = lookup.get(name.strip())
                    if tax_id:
                        nodes[tax_id].mark_ancestry_used()
                        nodes[tax_id].add_ancestral_total(1)
                    else:
                        LOGGER.warning("Could not find taxon for '%s'", name)


class ClassificationNode:  # pylint: disable=too-few-public-methods
    """A Dfam Classification node linked to its parent and children."""
    def __init__(self, class_id, parent_id, name, type_name, subtype_name):  # pylint: disable=too-many-arguments
        self.class_id = class_id
        self.parent_id = parent_id
        self.name = name
        self.type_name = type_name
        self.subtype_name = subtype_name

        self.parent_node = None
        self.children = []

    def full_name(self):
        """
        Returns the full name of this classification node, with the name of each
        classification level delimited by a semicolon.
        """
        name = self.name
        node = self.parent_node

        while node is not None:
            name = node.name + ";" + name
            node = node.parent_node

        return name


def load_classification(session):
    """Loads all classification nodes from the database."""
    nodes = {}

    LOGGER.info("Reading classification nodes")
    start = time.perf_counter()

    for (class_node, type_name, subtype_name) in session.query(
            dfam.Classification,
            dfam.RepeatmaskerType.name,
            dfam.RepeatmaskerSubtype.name,
        )\
        .outerjoin(dfam.RepeatmaskerType)\
        .outerjoin(dfam.RepeatmaskerSubtype)\
        .all():

        class_id = class_node.id
        parent_id = class_node.parent_id and int(class_node.parent_id)
        name = class_node.name
        nodes[class_id] = ClassificationNode(class_id, parent_id, name, type_name, subtype_name)

    for node in nodes.values():
        if node.parent_id is not None:
            node.parent_node = nodes[node.parent_id]
            node.parent_node.children += [node]

    delta = time.perf_counter() - start
    LOGGER.info("Loaded %d classification nodes in %f", len(nodes), delta)

    return nodes

def iterate_db_families(session, tax_db, families_query):
    """Returns an iterator over families in the Dfam MySQL database."""
    class_db = load_classification(session)

    # A "bakery" caches queries. The performance gains are worth it here, where
    # the queries are done many times with only the id changing. Another
    # approach that could be used is to make each of these queries once instead
    # of in a loop, but that would require a more significant restructuring.
    bakery = baked.bakery()

    clade_query = bakery(lambda s: s.query(dfam.t_family_clade.c.dfam_taxdb_tax_id))
    clade_query += lambda q: q.filter(dfam.t_family_clade.c.family_id == bindparam("id"))

    search_stage_query = bakery(lambda s: s.query(dfam.t_family_has_search_stage.c.repeatmasker_stage_id))
    search_stage_query += lambda q: q.filter(dfam.t_family_has_search_stage.c.family_id == bindparam("id"))

    buffer_stage_query = bakery(lambda s: s.query(
        dfam.FamilyHasBufferStage.repeatmasker_stage_id,
        dfam.FamilyHasBufferStage.start_pos,
        dfam.FamilyHasBufferStage.end_pos,
    ))
    buffer_stage_query += lambda q: q.filter(dfam.FamilyHasBufferStage.family_id == bindparam("id"))

    assembly_data_query = bakery(lambda s: s.query(
        dfam.Assembly.dfam_taxdb_tax_id,
        dfam.FamilyAssemblyDatum.hmm_hit_GA,
        dfam.FamilyAssemblyDatum.hmm_hit_TC,
        dfam.FamilyAssemblyDatum.hmm_hit_NC,
        dfam.FamilyAssemblyDatum.hmm_fdr,
    ))
    assembly_data_query += lambda q: q.filter(dfam.FamilyAssemblyDatum.family_id == bindparam("id"))
    assembly_data_query += lambda q: q.filter(dfam.Assembly.id == dfam.FamilyAssemblyDatum.assembly_id)

    feature_query = bakery(lambda s: s.query(dfam.FamilyFeature))
    feature_query += lambda q: q.filter(dfam.FamilyFeature.family_id == bindparam("id"))

    feature_attr_query = bakery(lambda s: s.query(dfam.FeatureAttribute))
    feature_attr_query += lambda q: q.filter(dfam.FeatureAttribute.family_feature_id == bindparam("id"))

    cds_query = bakery(lambda s: s.query(dfam.CodingSequence))
    cds_query += lambda q: q.filter(dfam.CodingSequence.family_id == bindparam("id"))

    alias_query = bakery(lambda s: s.query(dfam.FamilyDatabaseAlia))
    alias_query += lambda q: q.filter(dfam.FamilyDatabaseAlia.family_id == bindparam("id"))

    citation_query = bakery(lambda s: s.query(
        dfam.Citation.title,
        dfam.Citation.authors,
        dfam.Citation.journal,
        dfam.FamilyHasCitation.order_added,
    ))
    citation_query += lambda q: q.filter(dfam.Citation.pmid == dfam.FamilyHasCitation.citation_pmid)
    citation_query += lambda q: q.filter(dfam.FamilyHasCitation.family_id == bindparam("id"))

    hmm_query = bakery(lambda s: s.query(dfam.HmmModelDatum.hmm))
    hmm_query += lambda q: q.filter(dfam.HmmModelDatum.family_id == bindparam("id"))

    for record in families_query:
        family = famdb.Family()

        # REQUIRED FIELDS
        family.name = record.name
        family.accession = record.accession
        family.title = record.title
        family.version = record.version
        family.consensus = record.consensus
        family.length = record.length

        # RECOMMENDED FIELDS
        family.description = record.description
        family.author = record.author
        family.date_created = record.date_created
        family.date_modified = record.date_modified
        family.refineable = record.refineable
        family.target_site_cons = record.target_site_cons
        family.general_cutoff = record.hmm_general_threshold

        if record.classification_id in class_db:
            cls = class_db[record.classification_id]
            family.classification = cls.full_name()
            family.repeat_type = cls.type_name
            family.repeat_subtype = cls.subtype_name

        # clades and taxonomy links
        family.clades = []
        for (clade_id,) in clade_query(session).params(id=record.id).all():
            family.clades += [clade_id]

        # "SearchStages: A,B,C,..."
        ss_values = []
        for (stage_id,) in search_stage_query(session).params(id=record.id).all():
            ss_values += [str(stage_id)]

        if ss_values:
            family.search_stages = ",".join(ss_values)

        # "BufferStages:A,B,C[D-E],..."
        bs_values = []
        for (stage_id, start_pos, end_pos) in buffer_stage_query(session).params(id=record.id).all():
            if start_pos == 0 and end_pos == 0:
                bs_values += [str(stage_id)]
            else:
                bs_values += ["{}[{}-{}]".format(stage_id, start_pos, end_pos)]

        if bs_values:
            family.buffer_stages = ",".join(bs_values)

        # Taxa-specific thresholds. "ID, GA, TC, NC, fdr"
        th_values = []

        for (tax_id, spec_ga, spec_tc, spec_nc, spec_fdr) in assembly_data_query(session).params(id=record.id).all():
            th_values += ["{}, {}, {}, {}, {}".format(tax_id, spec_ga, spec_tc, spec_nc, spec_fdr)]
            tax_db[tax_id].mark_ancestry_used()

        if th_values:
            family.taxa_thresholds = "\n".join(th_values)

        feature_values = []
        for feature in feature_query(session).params(id=record.id).all():
            obj = {
                "type": feature.feature_type,
                "description": feature.description,
                "model_start_pos": feature.model_start_pos,
                "model_end_pos": feature.model_end_pos,
                "label": feature.label,
                "attributes": [],
            }

            for attribute in feature_attr_query(session).params(id=feature.id).all():
                obj["attributes"] += [{"attribute": attribute.attribute, "value": attribute.value}]
            feature_values += [obj]

        if feature_values:
            family.features = json.dumps(feature_values)

        cds_values = []
        for cds in cds_query(session).params(id=record.id).all():
            obj = {
                "product": cds.product,
                "translation": cds.translation,
                "cds_start": cds.cds_start,
                "cds_end": cds.cds_end,
                "exon_count": cds.exon_count,
                "exon_starts": str(cds.exon_starts),
                "exon_ends": str(cds.exon_ends),
                "external_reference": cds.external_reference,
                "reverse": (cds.reverse == 1),
                "stop_codons": cds.stop_codons,
                "frameshifts": cds.frameshifts,
                "gaps": cds.gaps,
                "percent_identity": cds.percent_identity,
                "left_unaligned": cds.left_unaligned,
                "right_unaligned": cds.right_unaligned,
                "description": cds.description,
                "protein_type": cds.protein_type,
            }

            cds_values += [obj]

        if cds_values:
            family.coding_sequences = json.dumps(cds_values)

        # External aliases

        alias_values = []
        for alias in alias_query(session).params(id=record.id).all():
            alias_values += ["%s: %s" % (alias.db_id, alias.db_link)]

        if alias_values:
            family.aliases = "\n".join(alias_values)

        citation_values = []
        for citation in citation_query(session).params(id=record.id).all():
            obj = {
                "title": citation.title,
                "authors": citation.authors,
                "journal": citation.journal,
                "order_added": citation.order_added,
            }
            citation_values += [obj]

        if citation_values:
            family.citations = json.dumps(citation_values)

        # MODEL DATA + METADATA

        hmm = hmm_query(session).params(id=record.id).one_or_none()
        if hmm:
            family.model = gzip.decompress(hmm[0]).decode()

        if record.hmm_maxl:
            family.max_length = record.hmm_maxl
        family.is_model_masked = record.model_mask

        seed_count = session.query(dfam.t_seed_region).filter(
            dfam.t_seed_region.c.family_id == record.id).count()
        family.seed_count = seed_count

        yield family


def run_export(args):  # pylint: disable=too-many-locals,too-many-branches,too-many-statements
    """Exports from a Dfam database to a FamDB file."""

    engine = sqlalchemy.create_engine(args.connection)
    session = sqlalchemy.orm.Session(bind=engine)

    tax_db = load_taxonomy(session)
    lookup = load_taxonomy_names(tax_db, session)

    for tid in args.taxon:
        tax_db[tid].mark_ancestry_used()

    db_version = session.query(dfam.DbVersion).one()
    version = db_version.dfam_version
    date = db_version.dfam_release_date.strftime("%Y-%m-%d")
    description = "Dfam - A database of transposable element (TE) sequence alignments and HMMs."
    copyright_text = \
"""Dfam - A database of transposable element (TE) sequence alignments and HMMs
Copyright (C) %d The Dfam consortium.

Release: Dfam_%s
Date   : %s

This database is free; you can redistribute it and/or modify it
as you wish, under the terms of the CC0 1.0 license, a
'no copyright' license:

The Dfam consortium has dedicated the work to the public domain, waiving
all rights to the work worldwide under copyright law, including all related
and neighboring rights, to the extent allowed by law.

You can copy, modify, distribute and perform the work, even for
commercial purposes, all without asking permission.
See Other Information below.


Other Information

o In no way are the patent or trademark rights of any person affected by
  CC0, nor are the rights that other persons may have in the work or in how
  the work is used, such as publicity or privacy rights.
o Makes no warranties about the work, and disclaims liability for all uses of the
  work, to the fullest extent permitted by applicable law.
o When using or citing the work, you should not imply endorsement by the Dfam consortium.

You may also obtain a copy of the CC0 license here:
http://creativecommons.org/publicdomain/zero/1.0/legalcode
""" % (db_version.dfam_release_date.year, version, date)
    args.outfile.set_db_info("Dfam", version, date, description, copyright_text)

    query = session.query(dfam.Family)

    if not args.include_raw:
        query = query.filter(dfam.Family.accession.like("DF%"))

    # TODO: This filter should be re-enabled later
    # .filter(dfam.Family.disabled != 1)

    target_count = query.count()
    LOGGER.info("Importing %d families", target_count)
    start = time.perf_counter()

    show_progress = LOGGER.getEffectiveLevel() > logging.DEBUG
    batches = 20
    batch_size = target_count // batches

    count = 0
    to_import = iterate_db_families(session, tax_db, query)

    for embl_file in args.extra_embl_file:
        to_import = itertools.chain(to_import, famdb.Family.read_embl_families(embl_file, lookup))

    for family in to_import:
        count += 1

        for clade_id in family.clades:
            # Associate the family to its relevant taxa and mark them as "used"
            tax_db[clade_id].families += [family.accession]
            tax_db[clade_id].mark_ancestry_used()

        args.outfile.add_family(family)
        LOGGER.debug("Imported family %s (%s)", family.name, family.accession)

        if show_progress and (count % batch_size) == 0:
            print("%5d / %5d" % (count, target_count))

    delta = time.perf_counter() - start
    LOGGER.info("Imported %d families in %f", count, delta)

    if args.extra_taxa_file:
        count_extra_taxa(tax_db, lookup, args.extra_taxa_file)
    calculate_ancestral_totals(tax_db)
    mark_used_threshold(tax_db, 200)

    args.outfile.write_taxonomy(tax_db)
    args.outfile.finalize()

    LOGGER.info("Finished import")


def main():
    """Parses command-line arguments and runs the import."""

    logging.basicConfig()

    parser = argparse.ArgumentParser()
    parser.add_argument("-l", "--log-level", default="INFO")
    parser.add_argument("-t", "--taxon", action="append", type=int, default=[])
    parser.add_argument("--extra-taxa-file")
    parser.add_argument("--extra-embl-file", action="append", default=[])
    parser.add_argument("-r", "--include-raw", action="store_true")
    parser.add_argument("connection")
    parser.add_argument("outfile", type=famdb_file_type("w"))

    args = parser.parse_args()
    logging.getLogger().setLevel(getattr(logging, args.log_level.upper()))
    run_export(args)


if __name__ == "__main__":
    main()
