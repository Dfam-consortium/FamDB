#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
    Export the dfam database to FamDB format.

    Usage: export_dfam.py [-h] [-l LOG_LEVEL]
               [--from-db mysql://...] [-r]
               [--from-tax-dump ncbi_tax/]
               [--from-embl file.embl [--from-embl file2.embl ...]]
               [--from-hmm file.hmm [--from-hmm file2.hmm ...]]
               [--db-version 3.2]
               [--db-date YYYY-MM-DD]
               [--count-taxa-in taxa.txt]
               outfile


    Data source options:

    --from-db                : Connection string to MySQL database to import from
    -r, --include-uncurated  : Include uncurated families (DR*) records, not only DF* (the default)
    --from-tax-dump          : Use taxonomy from NCBI database dump, instead of the database
                               (or if building from files instead of the database)
    --from-embl              : Additional Dfam EMBL-formatted file to import; can be given multiple times.
    --from-hmm               : Additional Dfam HMM-formatted file to import; can be given multiple times.

    --count-taxa-in : Counts taxa from a file (one line per "family") for the purpose of building and
                      filtering the taxonomy tree. The resulting file will include the taxonomy data
                      for each node with any families assigned and for each that occurs in a
                      count-taxa-in file.  Nodes with more families assigned to them in either way
                      also have more of their children included in the tree.

    Metadata options:

    --db-version    : Set the database version explicitly, overriding the version in --from-db if present.
    --db-date       : Set the database date explicitly, overriding the date in --from-db if present.
                      If not given, the current date will be used.

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
import datetime
import gzip
import itertools
import json
import logging
import os
import re
import time

import sqlalchemy
from sqlalchemy import bindparam
from sqlalchemy.ext import baked

import dfam_35 as dfam
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


def load_taxonomy_from_db(session):
    """
    Loads all taxonomy nodes and names from the database.

    Returns [nodes, lookup]

    nodes is a dict of tax_id to TaxNode objects.
    lookup is a dict of (sanitized) species name to tax_id.
    """

    nodes = {}

    LOGGER.info("Reading taxonomy nodes from database")
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

    LOGGER.info("Reading taxonomy names from database")
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

    return nodes, lookup


def load_taxonomy_from_dump(dump_dir):
    """
    Loads all taxonomy nodes and names from a dump of the NCBI
    taxonomy database (specifically, node.dmp and names.dmp).

    Returns [nodes, lookup]

    nodes is a dict of tax_id to TaxNode objects.
    lookup is a dict of (sanitized) species name to tax_id.
    """

    nodes = {}

    LOGGER.info("Reading taxonomy nodes from nodes.dmp")
    start = time.perf_counter()

    with open(os.path.join(dump_dir, "nodes.dmp")) as nodes_file:
        for line in nodes_file:
            fields = line.split("|")
            tax_id = int(fields[0])
            parent_id = int(fields[1])
            nodes[tax_id] = TaxNode(tax_id, parent_id)

    for node in nodes.values():
        if node.tax_id != 1:
            node.parent_node = nodes[node.parent_id]
            node.parent_node.children += [node]

    delta = time.perf_counter() - start
    LOGGER.info("Loaded %d taxonomy nodes in %f seconds", len(nodes), delta)

    LOGGER.info("Reading taxonomy names from names.dmp")
    start = time.perf_counter()

    lookup = {}

    with open(os.path.join(dump_dir, "names.dmp")) as names_file:
        for line in names_file:
            fields = line.split("|")
            tax_id = int(fields[0])
            name_txt = fields[1].strip()
            unique_name = fields[2].strip()
            name_class = fields[3].strip()

            name = unique_name or name_txt
            nodes[tax_id].names += [[name_class, name]]
            if name_class == "snientific name":
                sanitized_name = famdb.sanitize_name(name).lower()
                lookup[sanitized_name] = tax_id

    delta = time.perf_counter() - start
    LOGGER.info("Loaded taxonomy names in %f", delta)

    return nodes, lookup


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
    Counts species assignments from a file, to ensure that the necessary taxa
    are included in the famdb file ahead of time to support merging and queries
    for that dataset. Each line represents an entry, and is formatted as a
    comma-separated list of "sanitized names".
    """
    with open(filename) as file:
        for line in file:
            names = line.split(",")
            for name in names:
                name = name.strip().lower()
                tax_id = lookup.get(name)
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

    sequence_count_query = bakery(lambda s: s.query(dfam.SeedAlignDatum.sequence_count))
    sequence_count_query += lambda q: q.filter(dfam.SeedAlignDatum.family_id == bindparam("id"))

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
            if None in (spec_ga, spec_tc, spec_nc, spec_fdr):
                raise Exception("Found value of None for a threshold value for " +
                    record.accession + " in tax_id" + str(tax_id))
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

        seq_count = sequence_count_query(session).params(id=record.id).one_or_none()
        if seq_count:
            family.seed_count = seq_count[0]

        yield family

def read_hmm_families(filename, tax_db, tax_lookup):
    """
    Iterates over Family objects from the .hmm file 'filename'. The format
    should match the output format of to_hmm(), but this is not thoroughly
    tested.

    'tax_lookup' should be a dictionary of Species names (in the HMM file) to
    taxonomy IDs.
    """

    def set_family_code(family, code, value):
        """
        Sets an attribute on 'family' based on the HMM line starting with 'code'.
        For codes corresponding to list attributes, values are appended.
        """
        if code == "NAME":
            family.name = value
        elif code == "ACC":
            family.accession = value
        elif code == "DESC":
            family.description = value
        elif code == "LENG":
            family.length = int(value)
        elif code == "TH":
            match = re.match(r"TaxId:\s*(\d+);(\s*TaxName:\s*.*;)?\s*GA:\s*([\.\d]+);\s*TC:\s*([\.\d]+);\s*NC:\s*([\.\d]+);\s*fdr:\s*([\.\d]+);", value)
            if match:
                tax_id = int(match.group(1))
                tax_db[tax_id].mark_ancestry_used()
                tc_value = float(match.group(4))
                if family.general_cutoff is None or family.general_cutoff < tc_value:
                    family.general_cutoff = tc_value

                th_values = ", ".join([str(tax_id), match.group(3), match.group(4), match.group(5), match.group(6)])
                if family.taxa_thresholds is None:
                    family.taxa_thresholds = ""
                else:
                    family.taxa_thresholds += "\n"
                family.taxa_thresholds += th_values
            else:
                LOGGER.warning("Unrecognized format of TH line: <%s>", value)
        elif code == "CT":
            family.classification = value
        elif code == "MS":
            match = re.match(r"TaxId:\s*(\d+)", value)
            if match:
                family.clades += [int(match.group(1))]
            else:
                LOGGER.warning("Unrecognized format of MS line: <%s>", value)
        elif code == "CC":
            matches = re.match(r'\s*Type:\s*(\S+)', value)
            if matches:
                family.repeat_type = matches.group(1).strip()

            matches = re.match(r'\s*SubType:\s*(\S+)', value)
            if matches:
                family.repeat_subtype = matches.group(1).strip()

            matches = re.search(r'Species:\s*(.+)', value)
            if matches:
                for spec in matches.group(1).split(","):
                    name = spec.strip().lower()
                    if name:
                        tax_id = tax_lookup.get(name)
                        if tax_id:
                            if tax_id not in family.clades:
                                LOGGER.warning("MS line does not match RepeatMasker Species: line in '%s'!", name)
                        else:
                            LOGGER.warning("Could not find taxon for '%s'", name)

            matches = re.search(r'SearchStages:\s*(\S+)', value)
            if matches:
                family.search_stages = matches.group(1).strip()

            matches = re.search(r'BufferStages:\s*(\S+)', value)
            if matches:
                family.buffer_stages = matches.group(1).strip()

            matches = re.search('Refineable', value)
            if matches:
                family.refineable = True


    family = None
    in_metadata = False
    model = None

    with open(filename) as file:
        for line in file:
            if family is None:
                # HMMER3/f indicates start of metadata
                if line.startswith("HMMER3/f"):
                    family = famdb.Family()
                    family.clades = []
                    in_metadata = True
                    model = line
            else:
                if not any(map(line.startswith, ["GA", "TC", "NC", "TH", "BM", "SM", "CT", "MS", "CC"])):
                    model += line

                if in_metadata:
                    # HMM line indicates start of model
                    if line.startswith("HMM"):
                        in_metadata = False

                    # Continuing metadata
                    else:
                        code = line[:6].strip()
                        value = line[6:].rstrip("\n")
                        set_family_code(family, code, value)

                # '//' line indicates end of a model
                elif line.startswith("//"):
                    family.model = model
                    yield family
                    family = None


def run_export(args):  # pylint: disable=too-many-locals,too-many-branches,too-many-statements
    """Exports from a Dfam database to a FamDB file."""

    db_version = None
    db_date = None
    if args.from_db:
        engine = sqlalchemy.create_engine(args.from_db)
        session = sqlalchemy.orm.Session(bind=engine)

        if not args.from_tax_dump:
            tax_db, tax_lookup = load_taxonomy_from_db(session)

        version_info = session.query(dfam.DbVersion).one()
        db_version = version_info.dfam_version
        db_date = version_info.dfam_release_date.strftime("%Y-%m-%d")

    if args.from_tax_dump:
        tax_db, tax_lookup = load_taxonomy_from_dump(args.from_tax_dump)

    # Command-line overrides from db_version, db_date
    if args.db_version:
        db_version = args.db_version
    if args.db_date:
        db_date = args.db_date

    if not db_version:
        raise Exception("Could not determine database version. Please use --from-db or --db-version.")
    if not db_date:
        db_date = datetime.date.today().strftime("%Y-%m-%d")

    year_match = re.match(r'(\d{4})-', db_date)
    if year_match:
        db_year = year_match.group(1)
    else:
        raise Exception("Date should be in YYYY-MM-DD format, got: " + db_date)

    # TODO: make command-line options to customize these
    description = "Dfam - A database of transposable element (TE) sequence alignments and HMMs."
    copyright_text = \
"""Dfam - A database of transposable element (TE) sequence alignments and HMMs
Copyright (C) %s The Dfam consortium.

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
""" % (db_year, db_version, db_date)
    args.outfile.set_db_info("Dfam", db_version, db_date, description, copyright_text)

    to_import = []
    target_count = 0

    if args.from_db:
        query = session.query(dfam.Family)

        if not args.include_uncurated:
            query = query.filter(dfam.Family.accession.like("DF%"))

        # TODO: This filter should be re-enabled later
        # .filter(dfam.Family.disabled != 1)

        target_count += query.count()
        LOGGER.info("Including %d families from database", target_count)

        to_import = itertools.chain(to_import, iterate_db_families(session, tax_db, query))

    for embl_file in args.from_embl:
        LOGGER.info("Including all families from file: %s", embl_file)
        to_import = itertools.chain(to_import, famdb.Family.read_embl_families(embl_file, tax_lookup))

    for hmm_file in args.from_hmm:
        LOGGER.info("Including all families from file: %s", hmm_file)
        to_import = itertools.chain(to_import, read_hmm_families(hmm_file, tax_db, tax_lookup))

    start = time.perf_counter()


    show_progress = LOGGER.getEffectiveLevel() > logging.DEBUG
    batches = 20
    batch_size = target_count // batches
    count = 0

    if args.from_embl or args.from_hmm:
        LOGGER.info("File sources are not counted in advance; no progress will be reported")
        show_progress = False

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

    if args.count_taxa_in:
        count_extra_taxa(tax_db, tax_lookup, args.count_taxa_in)
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
    parser.add_argument("--from-db")
    parser.add_argument("--from-tax-dump")
    parser.add_argument("-r", "--include-uncurated", action="store_true")
    parser.add_argument("--from-embl", action="append", default=[])
    parser.add_argument("--from-hmm", action="append", default=[])
    parser.add_argument("--db-version")
    parser.add_argument("--db-date")
    parser.add_argument("--count-taxa-in")
    parser.add_argument("outfile", type=famdb_file_type("w"))

    args = parser.parse_args()
    logging.getLogger().setLevel(getattr(logging, args.log_level.upper()))
    run_export(args)


if __name__ == "__main__":
    main()
