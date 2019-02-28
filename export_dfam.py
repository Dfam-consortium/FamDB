#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
    Export the dfam database to FamDB format.

    Usage: export_dfam.py [-h] [-l LOG_LEVEL] connection_string outfile

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
import json
import logging
import time

import sqlalchemy

import dfam_dev
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

    def mark_ancestry_used(self):
        """Marks 'self' and all of its ancestors as 'used', up until the first 'used' ancestor."""
        node = self
        while node is not None:
            if node.used:
                break
            node.used = True
            node = node.parent_node


def famdb_file_type(mode):
    """Returns a type suitable for use with argparse, opening a FamDB file when active."""
    return lambda filename: famdb.FamDB(filename, mode)


def load_taxonomy(session):
    """Loads all taxonomy nodes from the database."""
    nodes = {}

    LOGGER.info("Reading taxonomy nodes")
    start = time.perf_counter()

    for tax_node in session.query(
            dfam_dev.NcbiTaxdbNode.tax_id,
            dfam_dev.NcbiTaxdbNode.parent_id
        ).all():
        nodes[tax_node.tax_id] = TaxNode(tax_node.tax_id, tax_node.parent_id)

    for node in nodes.values():
        if node.tax_id != 1:
            node.parent_node = nodes[node.parent_id]
            node.parent_node.children += [node]

    delta = time.perf_counter() - start
    LOGGER.info("Loaded %d taxonomy nodes in %f seconds", len(nodes), delta)

    return nodes


def load_used_taxonomy_names(nodes, session):
    """Loads the names of used taxonomy nodes from the database."""

    LOGGER.info("Reading taxonomy names")
    start = time.perf_counter()

    count = 0
    for node in nodes.values():
        if node.used:
            count += 1
            for tax_name in session.query(
                    dfam_dev.NcbiTaxdbName.name_txt,
                    dfam_dev.NcbiTaxdbName.name_class,
                ).filter(dfam_dev.NcbiTaxdbName.tax_id == node.tax_id):
                node.names += [[tax_name.name_class, tax_name.name_txt]]

            dfam_rec = session.query(dfam_dev.DfamTaxdb)\
                .filter(dfam_dev.DfamTaxdb.tax_id == node.tax_id)\
                .one_or_none()
            if dfam_rec:
                node.names += [["dfam sanitized name", dfam_rec.sanitized_name]]

    delta = time.perf_counter() - start
    LOGGER.info("Loaded names for %d used taxonomy nodes in %f", count, delta)


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
            dfam_dev.Classification,
            dfam_dev.RepeatmaskerType.name,
            dfam_dev.RepeatmaskerSubtype.name,
        )\
        .outerjoin(dfam_dev.RepeatmaskerType)\
        .outerjoin(dfam_dev.RepeatmaskerSubtype)\
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


def run_export(args):  # pylint: disable=too-many-locals,too-many-branches,too-many-statements
    """Exports from a Dfam database to a FamDB file."""

    engine = sqlalchemy.create_engine(args.connection)
    session = sqlalchemy.orm.Session(bind=engine)

    class_db = load_classification(session)
    tax_db = load_taxonomy(session)

    db_version = session.query(dfam_dev.DbVersion).one()
    version = db_version.dfam_version
    date = db_version.dfam_release_date.strftime("%Y-%m-%d")
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
    args.outfile.set_db_info("Dfam", version, date, copyright_text)

    query = session.query(dfam_dev.Family)
    # TODO: This filter should be re-enabled later
    # .filter(dfam_dev.Family.disabled != 1)

    target_count = query.count()
    LOGGER.info("Importing %d families", target_count)
    start = time.perf_counter()

    show_progress = LOGGER.getEffectiveLevel() > logging.DEBUG
    batches = 20
    batch_size = target_count // batches

    count = 0
    for record in query.all():
        count += 1

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
        for clade_record in session.query(dfam_dev.t_family_clade.c.dfam_taxdb_tax_id)\
            .filter(dfam_dev.t_family_clade.c.family_id == record.id)\
            .all():

            clade_id = clade_record.dfam_taxdb_tax_id

            family.clades += [clade_id]
            # Associate the family to its relevant taxa and mark them as "used"
            tax_db[clade_id].families += [family.accession]
            tax_db[clade_id].mark_ancestry_used()

        # "SearchStages: A,B,C,..."
        ss_values = []
        for ss_record in session.query(dfam_dev.t_family_has_search_stage)\
            .filter(dfam_dev.t_family_has_search_stage.c.family_id == record.id)\
            .all():

            ss_values += [str(ss_record.repeatmasker_stage_id)]

        if ss_values:
            family.search_stages = ",".join(ss_values)

        # "BufferStages:A,B,C[D-E],..."
        bs_values = []
        for bs_record in session.query(dfam_dev.FamilyHasBufferStage)\
            .filter(dfam_dev.FamilyHasBufferStage.family_id == record.id)\
            .all():

            stage_id = bs_record.repeatmasker_stage_id
            start_pos = bs_record.start_pos
            end_pos = bs_record.end_pos

            if start_pos == 0 and end_pos == 0:
                bs_values += [str(stage_id)]
            else:
                bs_values += ["{}[{}-{}]".format(stage_id, start_pos, end_pos)]

        if bs_values:
            family.buffer_stages = ",".join(bs_values)

        # Taxa-specific thresholds. "ID, GA, TC, NC, fdr"
        th_values = []

        for (spec_rec, tax_id) in session.query(
                dfam_dev.FamilyAssemblyDatum,
                dfam_dev.Assembly.dfam_taxdb_tax_id
            )\
            .filter(dfam_dev.FamilyAssemblyDatum.family_id == record.id)\
            .filter(dfam_dev.Assembly.id == dfam_dev.FamilyAssemblyDatum.assembly_id)\
            .all():

            th_values += ["{}, {}, {}, {}, {}".format(
                tax_id,
                spec_rec.hmm_hit_GA,
                spec_rec.hmm_hit_TC,
                spec_rec.hmm_hit_NC,
                spec_rec.hmm_fdr,
            )]

        if th_values:
            family.taxa_thresholds = "\n".join(th_values)

        feature_values = []
        for feature in session.query(dfam_dev.FamilyFeature)\
            .filter(dfam_dev.FamilyFeature.family_id == record.id)\
            .all():

            obj = {
                "type": feature.feature_type,
                "description": feature.description,
                "model_start_pos": feature.model_start_pos,
                "model_end_pos": feature.model_end_pos,
                "label": feature.label,
                "attributes": [],
            }

            for attribute in session.query(dfam_dev.FeatureAttribute)\
                .filter(dfam_dev.FeatureAttribute.family_feature_id == feature.id)\
                .all():

                obj["attributes"] += [{"attribute": attribute.attribute, "value": attribute.value}]

            feature_values += [obj]

        if feature_values:
            family.features = json.dumps(feature_values)

        cds_values = []
        for cds in session.query(dfam_dev.CodingSequence)\
            .filter(dfam_dev.CodingSequence.family_id == record.id)\
            .all():

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
        for alias in session.query(dfam_dev.FamilyDatabaseAlia)\
            .filter(dfam_dev.FamilyDatabaseAlia.family_id == record.id)\
            .all():

            alias_values += ["%s: %s" % (alias.db_id, alias.db_link)]

        if alias_values:
            family.aliases = "\n".join(alias_values)

        citation_values = []
        for citation in session.query(
                dfam_dev.Citation.title,
                dfam_dev.Citation.authors,
                dfam_dev.Citation.journal,
                dfam_dev.FamilyHasCitation.order_added,
            ).filter(dfam_dev.Citation.pmid == dfam_dev.FamilyHasCitation.citation_pmid)\
            .filter(dfam_dev.FamilyHasCitation.family_id == record.id)\
            .all():

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

        hmm = session.query(dfam_dev.HmmModelDatum.hmm).filter(
            dfam_dev.HmmModelDatum.family_id == record.id).one_or_none()
        if hmm:
            family.model = gzip.decompress(hmm[0]).decode()

        if record.hmm_maxl:
            family.max_length = record.hmm_maxl
        family.is_model_masked = record.model_mask

        seed_count = session.query(dfam_dev.t_seed_region).filter(
            dfam_dev.t_seed_region.c.family_id == record.id).count()
        family.seed_count = seed_count

        args.outfile.add_family(family)
        LOGGER.debug("Imported family %s (%s)", family.name, family.accession)

        if show_progress and (count % batch_size) == 0:
            print("%5d / %5d" % (count, target_count))

    delta = time.perf_counter() - start
    LOGGER.info("Imported %d families in %f", count, delta)

    load_used_taxonomy_names(tax_db, session)
    args.outfile.write_taxonomy(tax_db)

    LOGGER.info("Finished import")


def main():
    """Parses command-line arguments and runs the import."""

    logging.basicConfig()

    parser = argparse.ArgumentParser()
    parser.add_argument("-l", "--log-level", default="INFO")
    parser.add_argument("connection")
    parser.add_argument("outfile", type=famdb_file_type("w"))

    args = parser.parse_args()
    logging.getLogger().setLevel(getattr(logging, args.log_level.upper()))
    run_export(args)


if __name__ == "__main__":
    main()
