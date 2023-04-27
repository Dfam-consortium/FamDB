import time
import os
import gzip
import json
import re

from sqlalchemy import bindparam
from sqlalchemy.ext import baked

import dfam_35 as dfam
from famdb_helper_classes import TaxNode, ClassificationNode
from famdb_globals import LOGGER
import famdb


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
        dfam.NcbiTaxdbNode.tax_id, dfam.NcbiTaxdbNode.parent_id
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


def load_classification(session):
    """Loads all classification nodes from the database."""
    nodes = {}

    LOGGER.info("Reading classification nodes")
    start = time.perf_counter()

    for (class_node, type_name, subtype_name) in (
        session.query(
            dfam.Classification,
            dfam.RepeatmaskerType.name,
            dfam.RepeatmaskerSubtype.name,
        )
        .outerjoin(dfam.RepeatmaskerType)
        .outerjoin(dfam.RepeatmaskerSubtype)
        .all()
    ):

        class_id = class_node.id
        parent_id = class_node.parent_id and int(class_node.parent_id)
        name = class_node.name
        nodes[class_id] = ClassificationNode(
            class_id, parent_id, name, type_name, subtype_name
        )

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
    #
    # NOTE: This feature is deprecated in SQLAalchemy 1.4 and 2.0 and is rolled
    #       into the core behaviour.  To execute this query efficiently in the future
    #       we simply need to roll it into a function like so:
    # TODO: refactor
    #       def my_query(connection, parameter):
    #           stmt = select(dfam.t_family_clade)
    #           stmt = stmt.where(dfam.t_family_clade.c.dfam_taxdb_tax_id == parameter)
    #           return connection.execute(stmt)
    #
    #       Also to control the size of the cache simply pass query_cache_size to the
    #       engine creation statement like so:
    #
    #       engine = create_engine("mysql://.....", query_cache_size=1200)
    #
    #       See: https://docs.sqlalchemy.org/en/14/core/connections.html#sql-caching
    #
    bakery = baked.bakery()

    clade_query = bakery(lambda s: s.query(dfam.t_family_clade.c.dfam_taxdb_tax_id))
    clade_query += lambda q: q.filter(
        dfam.t_family_clade.c.family_id == bindparam("id")
    )

    search_stage_query = bakery(
        lambda s: s.query(dfam.t_family_has_search_stage.c.repeatmasker_stage_id)
    )
    search_stage_query += lambda q: q.filter(
        dfam.t_family_has_search_stage.c.family_id == bindparam("id")
    )

    buffer_stage_query = bakery(
        lambda s: s.query(
            dfam.FamilyHasBufferStage.repeatmasker_stage_id,
            dfam.FamilyHasBufferStage.start_pos,
            dfam.FamilyHasBufferStage.end_pos,
        )
    )
    buffer_stage_query += lambda q: q.filter(
        dfam.FamilyHasBufferStage.family_id == bindparam("id")
    )

    assembly_data_query = bakery(
        lambda s: s.query(
            dfam.Assembly.dfam_taxdb_tax_id,
            dfam.FamilyAssemblyDatum.hmm_hit_GA,
            dfam.FamilyAssemblyDatum.hmm_hit_TC,
            dfam.FamilyAssemblyDatum.hmm_hit_NC,
            dfam.FamilyAssemblyDatum.hmm_fdr,
        )
    )
    assembly_data_query += lambda q: q.filter(
        dfam.FamilyAssemblyDatum.family_id == bindparam("id")
    )
    assembly_data_query += lambda q: q.filter(
        dfam.Assembly.id == dfam.FamilyAssemblyDatum.assembly_id
    )

    feature_query = bakery(lambda s: s.query(dfam.FamilyFeature))
    feature_query += lambda q: q.filter(dfam.FamilyFeature.family_id == bindparam("id"))

    feature_attr_query = bakery(lambda s: s.query(dfam.FeatureAttribute))
    feature_attr_query += lambda q: q.filter(
        dfam.FeatureAttribute.family_feature_id == bindparam("id")
    )

    cds_query = bakery(lambda s: s.query(dfam.CodingSequence))
    cds_query += lambda q: q.filter(dfam.CodingSequence.family_id == bindparam("id"))

    alias_query = bakery(lambda s: s.query(dfam.FamilyDatabaseAlia))
    alias_query += lambda q: q.filter(
        dfam.FamilyDatabaseAlia.family_id == bindparam("id")
    )

    citation_query = bakery(
        lambda s: s.query(
            dfam.Citation.title,
            dfam.Citation.authors,
            dfam.Citation.journal,
            dfam.FamilyHasCitation.order_added,
        )
    )
    citation_query += lambda q: q.filter(
        dfam.Citation.pmid == dfam.FamilyHasCitation.citation_pmid
    )
    citation_query += lambda q: q.filter(
        dfam.FamilyHasCitation.family_id == bindparam("id")
    )

    hmm_query = bakery(lambda s: s.query(dfam.HmmModelDatum.hmm))
    hmm_query += lambda q: q.filter(dfam.HmmModelDatum.family_id == bindparam("id"))

    sequence_count_query = bakery(lambda s: s.query(dfam.SeedAlignDatum.sequence_count))
    sequence_count_query += lambda q: q.filter(
        dfam.SeedAlignDatum.family_id == bindparam("id")
    )

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
        for (stage_id, start_pos, end_pos) in (
            buffer_stage_query(session).params(id=record.id).all()
        ):
            if start_pos == 0 and end_pos == 0:
                bs_values += [str(stage_id)]
            else:
                bs_values += ["{}[{}-{}]".format(stage_id, start_pos, end_pos)]

        if bs_values:
            family.buffer_stages = ",".join(bs_values)

        # Taxa-specific thresholds. "ID, GA, TC, NC, fdr"
        th_values = []

        for (tax_id, spec_ga, spec_tc, spec_nc, spec_fdr) in (
            assembly_data_query(session).params(id=record.id).all()
        ):
            if None in (spec_ga, spec_tc, spec_nc, spec_fdr):
                raise Exception(
                    "Found value of None for a threshold value for "
                    + record.accession
                    + " in tax_id"
                    + str(tax_id)
                )
            th_values += [
                "{}, {}, {}, {}, {}".format(tax_id, spec_ga, spec_tc, spec_nc, spec_fdr)
            ]
            # tax_db[tax_id].mark_ancestry_used()
            tax_db[tax_id].used = True

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
                obj["attributes"] += [
                    {"attribute": attribute.attribute, "value": attribute.value}
                ]
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
            match = re.match(
                r"TaxId:\s*(\d+);(\s*TaxName:\s*.*;)?\s*GA:\s*([\.\d]+);\s*TC:\s*([\.\d]+);\s*NC:\s*([\.\d]+);\s*fdr:\s*([\.\d]+);",
                value,
            )
            if match:
                tax_id = int(match.group(1))
                # tax_db[tax_id].mark_ancestry_used()
                tax_db[tax_id].used = True
                tc_value = float(match.group(4))
                if family.general_cutoff is None or family.general_cutoff < tc_value:
                    family.general_cutoff = tc_value

                th_values = ", ".join(
                    [
                        str(tax_id),
                        match.group(3),
                        match.group(4),
                        match.group(5),
                        match.group(6),
                    ]
                )
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
            matches = re.match(r"\s*Type:\s*(\S+)", value)
            if matches:
                family.repeat_type = matches.group(1).strip()

            matches = re.match(r"\s*SubType:\s*(\S+)", value)
            if matches:
                family.repeat_subtype = matches.group(1).strip()

            matches = re.search(r"Species:\s*(.+)", value)
            if matches:
                for spec in matches.group(1).split(","):
                    name = spec.strip().lower()
                    if name:
                        tax_id = tax_lookup.get(name)
                        if tax_id:
                            if tax_id not in family.clades:
                                LOGGER.warning(
                                    "MS line does not match RepeatMasker Species: line in '%s'!",
                                    name,
                                )
                        else:
                            LOGGER.warning("Could not find taxon for '%s'", name)

            matches = re.search(r"SearchStages:\s*(\S+)", value)
            if matches:
                family.search_stages = matches.group(1).strip()

            matches = re.search(r"BufferStages:\s*(\S+)", value)
            if matches:
                family.buffer_stages = matches.group(1).strip()

            matches = re.search("Refineable", value)
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
                if not any(
                    map(
                        line.startswith,
                        ["GA", "TC", "NC", "TH", "BM", "SM", "CT", "MS", "CC"],
                    )
                ):
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
