import time
import itertools
import os
import gzip
import json
import re
import sys
from collections import defaultdict

from sqlalchemy import select

sys.path.append(os.path.join(os.path.dirname(__file__), "../Schemata/ORMs/python"))
import dfamorm as dfam

sys.path.append(os.path.join(os.path.dirname(__file__), "../FamDB"))
from famdb_helper_classes import TaxNode, ClassificationNode, Family
from famdb_helper_methods import sanitize_name
import logging
LOGGER = logging.getLogger(__name__)


def load_taxonomy_from_db(session, relevant_nodes):
    """
    Loads all taxonomy nodes and names from the database.

    Returns [nodes, lookup]

    nodes is a dict of tax_id to TaxNode objects.
    lookup is a dict of (sanitized) species name to tax_id.
    """

    nodes = {}

    LOGGER.info("Reading taxonomy nodes from database")
    start = time.perf_counter()

    for tax_node in session.execute(
        select(dfam.NcbiTaxdbNodes.tax_id, dfam.NcbiTaxdbNodes.parent_id).where(
            dfam.NcbiTaxdbNodes.tax_id.in_(relevant_nodes)
        )
    ).all():
        nodes[tax_node.tax_id] = TaxNode(tax_node.tax_id, tax_node.parent_id)

    for node in nodes.values():
        if node.tax_id != 1:
            node.parent_node = nodes.get(node.parent_id)
            if node.parent_node:
                node.parent_node.children += [node]

    delta = time.perf_counter() - start
    LOGGER.info("Loaded %d taxonomy nodes in %.1f seconds", len(nodes), delta)

    LOGGER.info("Reading taxonomy names from database")
    start = time.perf_counter()

    lookup = {}

    # Load *all* names. As the number of included names grows large this
    # is actually faster than loading only the needed ones from the
    # database, at the cost of memory usage TODO fix this with the filter/partition loop
    for entry in session.execute(
        select(
            dfam.NcbiTaxdbNames.tax_id,
            dfam.NcbiTaxdbNames.name_txt,
            dfam.NcbiTaxdbNames.unique_name,
            dfam.NcbiTaxdbNames.name_class,
            dfam.NcbiTaxdbNames.sanitized_name,
        ).where(dfam.NcbiTaxdbNames.tax_id.in_(relevant_nodes))
    ):
        name = entry.unique_name or entry.name_txt
        name_class = entry.name_class
        nodes[entry.tax_id].names += [
            [name_class, name],
            [f"sanitized {name_class}", entry.sanitized_name],
        ]
        if name_class == "scientific name":
            # sanitized_name = sanitize_name(name).lower()
            lookup[entry.sanitized_name.lower()] = entry.tax_id

    delta = time.perf_counter() - start
    LOGGER.info("Loaded taxonomy names in %.1f seconds", delta)

    return nodes, lookup


def load_taxonomy_from_dump(dump_dir, relevant_nodes):
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
            if tax_id in relevant_nodes:
                parent_id = int(fields[1])
                nodes[tax_id] = TaxNode(tax_id, parent_id)

    for node in nodes.values():
        if node.tax_id != 1:
            node.parent_node = nodes[node.parent_id]
            node.parent_node.children += [node]

    delta = time.perf_counter() - start
    LOGGER.info("Loaded %d taxonomy nodes in %.1f seconds", len(nodes), delta)

    LOGGER.info("Reading taxonomy names from names.dmp")
    start = time.perf_counter()

    lookup = {}

    with open(os.path.join(dump_dir, "names.dmp")) as names_file:
        for line in names_file:
            fields = line.split("|")
            tax_id = int(fields[0])
            if tax_id in relevant_nodes:
                name_txt = fields[1].strip()
                unique_name = fields[2].strip()
                name_class = fields[3].strip()

                name = unique_name or name_txt
                nodes[tax_id].names += [[name_class, name]]
                if name_class == "scientific name":
                    sanitized_name = sanitize_name(name).lower()
                    lookup[sanitized_name] = tax_id

    delta = time.perf_counter() - start
    LOGGER.info("Loaded taxonomy names in %.1f seconds", delta)

    return nodes, lookup


def load_classification(session):
    """Loads all classification nodes from the database."""
    nodes = {}

    LOGGER.debug("Reading classification nodes")
    start = time.perf_counter()

    for class_node, type_name, subtype_name in session.execute(
        select(
            dfam.Classification,
            dfam.RepeatmaskerType.name,
            dfam.RepeatmaskerSubtype.name,
        )
        .outerjoin(dfam.RepeatmaskerType)
        .outerjoin(dfam.RepeatmaskerSubtype)
    ).all():

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
    LOGGER.debug("Loaded %d classification nodes in %.1f seconds", len(nodes), delta)

    return nodes


def _fetch_batch_data(session, records, is_hmm, timing_stats=None,
                      families_with_features=None):
    """Fire one bulk query per relationship type for a list of family records.

    Returns a dict of maps keyed by family_id, one entry per relationship type.
    is_hmm controls whether HMM-specific queries (blobs, thresholds) are fired.
    timing_stats: optional defaultdict(float) accumulator; elapsed seconds are
    added under keys like "q_clades", "q_hmm", etc.
    families_with_features: optional frozenset of family_ids known to have
    features.  When provided, the features query is skipped entirely for batches
    where none of the IDs appear in the set, eliminating redundant table scans.
    """
    ids = [r.id for r in records]

    def _t0():
        return time.perf_counter()

    def _acc(key, t_start):
        if timing_stats is not None:
            timing_stats[key] += time.perf_counter() - t_start

    # clades: {family_id: [tax_id, ...]}
    clades_map = defaultdict(list)
    _ts = _t0()
    for row in session.execute(
        select(
            dfam.t_family_clade.c.family_id,
            dfam.t_family_clade.c.dfam_taxdb_tax_id,
        ).where(dfam.t_family_clade.c.family_id.in_(ids))
    ):
        clades_map[row.family_id].append(row.dfam_taxdb_tax_id)
    _acc("q_clades", _ts)

    # search stages: {family_id: [stage_id, ...]}
    search_stages_map = defaultdict(list)
    _ts = _t0()
    for row in session.execute(
        select(
            dfam.t_family_has_search_stage.c.family_id,
            dfam.t_family_has_search_stage.c.repeatmasker_stage_id,
        ).where(dfam.t_family_has_search_stage.c.family_id.in_(ids))
    ):
        search_stages_map[row.family_id].append(row.repeatmasker_stage_id)
    _acc("q_search_stages", _ts)

    # buffer stages: {family_id: [(stage_id, start, end), ...]}
    buffer_stages_map = defaultdict(list)
    _ts = _t0()
    for row in session.execute(
        select(
            dfam.FamilyHasBufferStage.family_id,
            dfam.FamilyHasBufferStage.repeatmasker_stage_id,
            dfam.FamilyHasBufferStage.start_pos,
            dfam.FamilyHasBufferStage.end_pos,
        ).where(dfam.FamilyHasBufferStage.family_id.in_(ids))
    ):
        buffer_stages_map[row.family_id].append(
            (row.repeatmasker_stage_id, row.start_pos, row.end_pos)
        )
    _acc("q_buffer_stages", _ts)

    # taxa-specific thresholds - HMM component only
    # {family_id: [(tax_id, ga, tc, nc, fdr), ...]}
    assembly_map = defaultdict(list)
    if is_hmm:
        _ts = _t0()
        for row in session.execute(
            select(
                dfam.FamilyAssemblyData.family_id,
                dfam.Assembly.dfam_taxdb_tax_id,
                dfam.FamilyAssemblyData.hmm_hit_GA,
                dfam.FamilyAssemblyData.hmm_hit_TC,
                dfam.FamilyAssemblyData.hmm_hit_NC,
                dfam.FamilyAssemblyData.hmm_fdr,
            )
            .where(dfam.FamilyAssemblyData.family_id.in_(ids))
            .where(dfam.Assembly.id == dfam.FamilyAssemblyData.assembly_id)
        ):
            assembly_map[row.family_id].append(
                (
                    row.dfam_taxdb_tax_id,
                    row.hmm_hit_GA,
                    row.hmm_hit_TC,
                    row.hmm_hit_NC,
                    row.hmm_fdr,
                )
            )
        _acc("q_assembly", _ts)

    # features: two-level query - features first, then attributes for all feature IDs
    # {family_id: [feature_dict, ...]}
    # Skipped entirely when families_with_features is provided and none of the
    # current batch IDs appear in it, avoiding redundant table scans.
    features_map = defaultdict(list)
    _ts = _t0()
    batch_has_features = (
        families_with_features is None
        or any(fid in families_with_features for fid in ids)
    )
    if batch_has_features:
        feature_rows_by_id = {}
        family_for_feature = {}
        for row in session.execute(
            select(dfam.FamilyFeature).where(dfam.FamilyFeature.family_id.in_(ids))
        ).scalars():
            feature_rows_by_id[row.id] = row
            family_for_feature[row.id] = row.family_id

        if feature_rows_by_id:
            attr_map = defaultdict(list)
            for row in session.execute(
                select(dfam.FeatureAttribute).where(
                    dfam.FeatureAttribute.family_feature_id.in_(feature_rows_by_id)
                )
            ).scalars():
                attr_map[row.family_feature_id].append(row)

            for feat_id, feat in feature_rows_by_id.items():
                obj = {
                    "type": feat.feature_type,
                    "description": feat.description,
                    "model_start_pos": feat.model_start_pos,
                    "model_end_pos": feat.model_end_pos,
                    "label": feat.label,
                    "attributes": [
                        {"attribute": a.attribute, "value": a.value}
                        for a in attr_map[feat_id]
                    ],
                }
                features_map[family_for_feature[feat_id]].append(obj)
    _acc("q_features", _ts)

    # CDS: {family_id: [cds_dict, ...]}
    cds_map = defaultdict(list)
    _ts = _t0()
    for row in session.execute(
        select(dfam.CodingSequence).where(dfam.CodingSequence.family_id.in_(ids))
    ).scalars():
        cds_map[row.family_id].append(
            {
                "product": row.product,
                "translation": row.translation,
                "cds_start": row.cds_start,
                "cds_end": row.cds_end,
                "exon_count": row.exon_count,
                "exon_starts": str(row.exon_starts),
                "exon_ends": str(row.exon_ends),
                "external_reference": row.external_reference,
                "reverse": (row.reverse == 1),
                "stop_codons": row.stop_codons,
                "frameshifts": row.frameshifts,
                "gaps": row.gaps,
                "percent_identity": row.percent_identity,
                "left_unaligned": row.left_unaligned,
                "right_unaligned": row.right_unaligned,
                "description": row.description,
                "protein_type": row.protein_type,
            }
        )
    _acc("q_cds", _ts)

    # aliases: {family_id: [str, ...]}
    alias_map = defaultdict(list)
    _ts = _t0()
    for row in session.execute(
        select(dfam.FamilyDatabaseAlias).where(
            dfam.FamilyDatabaseAlias.family_id.in_(ids)
        )
    ).scalars():
        alias_map[row.family_id].append(f"{row.db_id}: {row.db_link}")
    _acc("q_aliases", _ts)

    # authors: {family_id: "Name; Name"}, in the same format as
    # Lib/DfamAttribution.get_family_author_string
    author_names = defaultdict(list)
    _ts = _t0()
    for row in session.execute(
        select(dfam.FamilyAttribution.family_id, dfam.Contributor.full_name)
        .join(
            dfam.Contributor,
            dfam.Contributor.id == dfam.FamilyAttribution.contributor_id,
        )
        .where(dfam.FamilyAttribution.family_id.in_(ids))
        .where(dfam.FamilyAttribution.attribution_type == "author")
        .order_by(dfam.FamilyAttribution.family_id, dfam.FamilyAttribution.sort_order)
    ):
        author_names[row.family_id].append(row.full_name)
    author_map = {fid: "; ".join(names) for fid, names in author_names.items()}
    _acc("q_authors", _ts)

    # citations: {family_id: [citation_dict, ...]}
    citation_map = defaultdict(list)
    _ts = _t0()
    for row in session.execute(
        select(
            dfam.FamilyHasCitation.family_id,
            dfam.Citation.title,
            dfam.Citation.authors,
            dfam.Citation.journal,
            dfam.FamilyHasCitation.order_added,
        )
        .where(dfam.FamilyHasCitation.family_id.in_(ids))
        .where(dfam.Citation.doi == dfam.FamilyHasCitation.citation_doi)
    ):
        citation_map[row.family_id].append(
            {
                "title": row.title,
                "authors": row.authors,
                "journal": row.journal,
                "order_added": row.order_added,
            }
        )
    _acc("q_citations", _ts)

    # HMM blobs - HMM component only: {family_id: compressed_blob}
    hmm_map = {}
    if is_hmm:
        _ts = _t0()
        for row in session.execute(
            select(dfam.HmmModelData.family_id, dfam.HmmModelData.hmm).where(
                dfam.HmmModelData.family_id.in_(ids)
            )
        ):
            hmm_map[row.family_id] = row.hmm
        _acc("q_hmm", _ts)

    # seed alignment counts: {family_id: count}
    seq_count_map = {}
    _ts = _t0()
    for row in session.execute(
        select(dfam.SeedAlignData.family_id, dfam.SeedAlignData.sequence_count).where(
            dfam.SeedAlignData.family_id.in_(ids)
        )
    ):
        seq_count_map[row.family_id] = row.sequence_count
    _acc("q_seq_count", _ts)

    return {
        "clades": clades_map,
        "search_stages": search_stages_map,
        "buffer_stages": buffer_stages_map,
        "assembly": assembly_map,
        "features": features_map,
        "cds": cds_map,
        "aliases": alias_map,
        "authors": author_map,
        "citations": citation_map,
        "hmm": hmm_map,
        "seq_count": seq_count_map,
    }


def _build_family(record, bd, class_db, is_hmm, defer_model_decompress=False):
    """Populate a Family object from a DB record and pre-fetched batch data.

    defer_model_decompress: if True, skip gzip.decompress for the HMM blob -
    the caller is responsible for decompressing and setting family.model before
    use.  The blob is available via bd["hmm"].get(record.id).
    """
    family = Family()

    # REQUIRED FIELDS
    family.name = record.name
    family.accession = record.accession
    family.title = record.title
    family.version = record.version
    family.consensus = record.consensus
    family.length = record.length

    # RECOMMENDED FIELDS
    family.description = record.description
    family.author = bd["authors"].get(record.id)
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

    # clades
    family.clades = bd["clades"].get(record.id, [])

    # search stages: "A,B,C,..."
    ss = bd["search_stages"].get(record.id)
    if ss:
        family.search_stages = ",".join(str(s) for s in ss)

    # buffer stages: "A,B,C[D-E],..."
    bs_values = []
    for stage_id, start_pos, end_pos in bd["buffer_stages"].get(record.id, []):
        if start_pos == 0 and end_pos == 0:
            bs_values.append(str(stage_id))
        else:
            bs_values.append(f"{stage_id}[{start_pos}-{end_pos}]")
    if bs_values:
        family.buffer_stages = ",".join(bs_values)

    # taxa-specific thresholds - HMM component only
    if is_hmm:
        th_values = []
        for tax_id, spec_ga, spec_tc, spec_nc, spec_fdr in bd["assembly"].get(
            record.id, []
        ):
            if record.accession.startswith("DF") and None in (
                spec_ga,
                spec_tc,
                spec_nc,
                spec_fdr,
            ):
                raise Exception(
                    "Found value of None for a threshold value for "
                    + record.accession
                    + " in tax_id "
                    + str(tax_id)
                )
            th_values.append(f"{tax_id}, {spec_ga}, {spec_tc}, {spec_nc}, {spec_fdr}")
        if th_values:
            family.taxa_thresholds = "\n".join(th_values)

    feature_values = bd["features"].get(record.id)
    if feature_values:
        family.features = json.dumps(feature_values)

    cds_values = bd["cds"].get(record.id)
    if cds_values:
        family.coding_sequences = json.dumps(cds_values)

    alias_values = bd["aliases"].get(record.id)
    if alias_values:
        family.aliases = "\n".join(alias_values)

    citation_values = bd["citations"].get(record.id)
    if citation_values:
        family.citations = json.dumps(citation_values)

    # MODEL DATA + METADATA - HMM component only
    if is_hmm:
        hmm_blob = bd["hmm"].get(record.id)
        if hmm_blob and not defer_model_decompress:
            family.model = gzip.decompress(hmm_blob).decode()
        if record.hmm_maxl:
            family.max_length = record.hmm_maxl
        family.is_model_masked = record.model_mask

    seq_count = bd["seq_count"].get(record.id)
    if seq_count:
        family.seed_count = seq_count

    return family


def iterate_db_families(session, families_query, is_hmm=True, batch_size=500):
    """Returns an iterator over families from a streaming SQLAlchemy query.

    Fetches relationship data in bulk using batched IN queries, reducing SQL
    round-trips from O(N * 8) to O(ceil(N/batch_size) * 8).

    is_hmm: if False, skips HMM blob and per-assembly threshold queries.
    batch_size: number of families per bulk query round-trip.
    """
    class_db = load_classification(session)
    it = iter(families_query)
    while True:
        batch = list(itertools.islice(it, batch_size))
        if not batch:
            break
        batch_data = _fetch_batch_data(session, batch, is_hmm)
        for record in batch:
            yield _build_family(record, batch_data, class_db, is_hmm)


def iterate_db_families_by_ids(session, family_ids, is_hmm=True, batch_size=500,
                               defer_model_decompress=False):
    """Returns an iterator over families fetched by primary key list.

    Unlike iterate_db_families, this does not require a pre-built streaming
    query - it fetches family records directly by ID in batches, making it
    suitable for use when the set of family IDs is pre-computed (e.g. from
    precompute_family_partitions).

    is_hmm: if False, skips HMM blob and per-assembly threshold queries.
    batch_size: number of family IDs per bulk query round-trip.
    defer_model_decompress: if True (HMM components only), skip gzip.decompress
    in the worker and yield (Family, raw_gzip_bytes) tuples instead of plain
    Family objects.  The caller decompresses right before writing to HDF5,
    keeping pickle files small and saving per-worker CPU.

    Logs a per-query timing breakdown at INFO level when the iterator is
    exhausted (or closed).  This reveals which SQL relationship query
    (clades, hmm blobs, assembly thresholds, ...) is consuming the most wall
    time so bottlenecks can be targeted.
    """
    class_db = load_classification(session)
    timing = defaultdict(float)
    total = 0
    try:
        # Pre-scan: one pass over the full family_ids list to find which IDs
        # actually have features.  Uses larger batches (10k) than the main loop
        # since we only fetch integer PKs.  This single pass replaces
        # len(family_ids)/batch_size redundant per-batch features queries for
        # the common case where most batches have no features at all.
        _ts = time.perf_counter()
        families_with_features = set()
        prescan_batch = 10_000
        it_pre = iter(family_ids)
        while True:
            pre_batch = list(itertools.islice(it_pre, prescan_batch))
            if not pre_batch:
                break
            for fid in session.execute(
                select(dfam.FamilyFeature.family_id)
                .where(dfam.FamilyFeature.family_id.in_(pre_batch))
                .distinct()
            ).scalars():
                families_with_features.add(fid)
        families_with_features = frozenset(families_with_features)
        timing["t_prescan_features"] += time.perf_counter() - _ts
        LOGGER.debug(
            "Features pre-scan: %d of %d families have features",
            len(families_with_features), len(family_ids),
        )

        it = iter(family_ids)
        while True:
            id_batch = list(itertools.islice(it, batch_size))
            if not id_batch:
                break

            _ts = time.perf_counter()
            records = session.execute(
                select(dfam.Family)
                .where(dfam.Family.id.in_(id_batch))
                .order_by(dfam.Family.id)
            ).scalars().all()
            timing["t_main_query"] += time.perf_counter() - _ts

            if not records:
                continue

            batch_data = _fetch_batch_data(session, records, is_hmm, timing,
                                           families_with_features=families_with_features)

            _ts = time.perf_counter()
            for record in records:
                family = _build_family(record, batch_data, class_db, is_hmm,
                                       defer_model_decompress=defer_model_decompress)
                if defer_model_decompress and is_hmm:
                    yield family, batch_data["hmm"].get(record.id)
                else:
                    yield family
                total += 1
            timing["t_build"] += time.perf_counter() - _ts
    finally:
        if total > 0:
            n = total
            # Build a compact per-query summary (ms per family)
            def _ms(key):
                return timing[key] / n * 1000

            lines = [
                f"prescan={timing['t_prescan_features']:.1f}s(once)",
                f"main_q={_ms('t_main_query'):.2f}ms",
                f"clades={_ms('q_clades'):.2f}ms",
                f"stages={_ms('q_search_stages') + _ms('q_buffer_stages'):.2f}ms",
            ]
            if is_hmm:
                lines += [
                    f"assembly={_ms('q_assembly'):.2f}ms",
                    f"hmm_blob={_ms('q_hmm'):.2f}ms",
                ]
            lines += [
                f"features={_ms('q_features'):.2f}ms",
                f"cds={_ms('q_cds'):.2f}ms",
                f"aliases={_ms('q_aliases'):.2f}ms",
                f"authors={_ms('q_authors'):.2f}ms",
                f"citations={_ms('q_citations'):.2f}ms",
                f"seq_count={_ms('q_seq_count'):.2f}ms",
                f"build={_ms('t_build'):.2f}ms",
            ]
            total_ms = sum(timing.values()) / n * 1000
            LOGGER.debug(
                "DB timing (%d families, %.2fms/family total): %s",
                n, total_ms, "  ".join(lines),
            )


def read_hmm_families(filename, tax_lookup, nodes):
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
                    family = Family()
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
                    for clade in family.clades:
                        if clade in nodes:
                            LOGGER.info(
                                f"Including {family.accession} in taxa {clade} from {filename}"
                            )
                            yield family
                    family = None
