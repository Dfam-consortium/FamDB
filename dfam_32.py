# coding: utf-8
from sqlalchemy import Column, Date, DateTime, Enum, Float, ForeignKey, Index, LargeBinary, String, Table, Text, text
from sqlalchemy.dialects.mysql import BIGINT, INTEGER, LONGBLOB, LONGTEXT, MEDIUMINT, MEDIUMTEXT, SMALLINT, TINYINT, TINYTEXT
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()
metadata = Base.metadata


class Citation(Base):
    __tablename__ = 'citation'

    pmid = Column(INTEGER(10), primary_key=True)
    title = Column(TINYTEXT)
    authors = Column(MEDIUMTEXT)
    journal = Column(TINYTEXT)
    pubdate = Column(Date)


class CurationState(Base):
    __tablename__ = 'curation_state'

    id = Column(BIGINT(20), primary_key=True)
    name = Column(String(45))
    description = Column(String(255))


class DbVersion(Base):
    __tablename__ = 'db_version'

    dfam_version = Column(String(45), primary_key=True, nullable=False)
    dfam_release_date = Column(Date, primary_key=True, nullable=False)


class DeadFamily(Base):
    __tablename__ = 'dead_family'

    accession = Column(String(45), primary_key=True)
    name = Column(String(45))
    comment = Column(MEDIUMTEXT)
    user = Column(INTEGER(11))
    deleted = Column(DateTime)


class DfamTaxdb(Base):
    __tablename__ = 'dfam_taxdb'

    tax_id = Column(BIGINT(20), primary_key=True)
    scientific_name = Column(String(128), nullable=False)
    sanitized_name = Column(String(128), nullable=False)
    common_name = Column(String(128))
    unique_name = Column(String(128))
    lineage = Column(MEDIUMTEXT)

    familys = relationship('Family', secondary='family_clade')


class NcbiGencode(Base):
    __tablename__ = 'ncbi_gencode'

    genetic_code_id = Column(INTEGER(10), primary_key=True)
    abbreviation = Column(String(40))
    name = Column(String(80))
    cde = Column(String(80))
    starts = Column(String(80))


class NcbiTaxdbName(Base):
    __tablename__ = 'ncbi_taxdb_names'

    tax_id = Column(BIGINT(20), primary_key=True, nullable=False, index=True)
    name_txt = Column(String(128), primary_key=True, nullable=False, index=True)
    unique_name = Column(String(128), primary_key=True, nullable=False, index=True)
    name_class = Column(String(128), primary_key=True, nullable=False, index=True)
    sanitized_name = Column(String(128), index=True)


class NcbiTaxdbNode(Base):
    __tablename__ = 'ncbi_taxdb_nodes'

    tax_id = Column(BIGINT(20), primary_key=True, unique=True)
    parent_id = Column(BIGINT(20), index=True)
    rank = Column(String(128))
    embl_code = Column(String(4))
    division_id = Column(BIGINT(20))
    inherited_div = Column(TINYINT(1))
    genetic_code_id = Column(BIGINT(20))
    inherited_GC = Column(TINYINT(1))
    mitochondrial_genetic_code_id = Column(BIGINT(20))
    inherited_MGC_flag = Column(TINYINT(1))
    GenBank_hidden_flag = Column(TINYINT(1))
    hidden_subtree_root_flag = Column(TINYINT(1))
    comments = Column(LargeBinary)


t_next_accession = Table(
    'next_accession', metadata,
    Column('next_acc_id', BIGINT(20), nullable=False, server_default=text("'0'"))
)


class RepeatmaskerStage(Base):
    __tablename__ = 'repeatmasker_stage'

    id = Column(BIGINT(20), primary_key=True, unique=True)
    name = Column(String(25), nullable=False, unique=True)
    description = Column(String(128), nullable=False)


class RepeatmaskerSubtype(Base):
    __tablename__ = 'repeatmasker_subtype'

    id = Column(BIGINT(20), primary_key=True, unique=True)
    name = Column(String(25), nullable=False, unique=True)
    description = Column(String(128))
    parent_type_id = Column(BIGINT(20), nullable=False)


class RepeatmaskerType(Base):
    __tablename__ = 'repeatmasker_type'

    id = Column(BIGINT(20), primary_key=True)
    name = Column(String(25), nullable=False, unique=True)
    description = Column(String(128))


class SourceMethod(Base):
    __tablename__ = 'source_method'

    id = Column(BIGINT(20), primary_key=True)
    name = Column(String(45))
    description = Column(String(255))


class Wikipedia(Base):
    __tablename__ = 'wikipedia'

    auto_wiki = Column(INTEGER(10), primary_key=True)
    title = Column(TINYTEXT, nullable=False, index=True)
    wikitext = Column(LONGTEXT)

    classifications = relationship('Classification', secondary='classification_has_wikipedia')


class Assembly(Base):
    __tablename__ = 'assembly'

    id = Column(BIGINT(20), primary_key=True)
    name = Column(String(45), nullable=False, unique=True)
    description = Column(String(100))
    dfam_taxdb_tax_id = Column(ForeignKey('dfam_taxdb.tax_id'), nullable=False, index=True)
    source = Column(String(20))
    release_date = Column(DateTime)
    version = Column(String(45))
    uri = Column(Text)
    schema_name = Column(String(45))
    visible = Column(INTEGER(11), server_default=text("'0'"))
    display_order = Column(INTEGER(11), server_default=text("'0'"))
    z_size = Column(BIGINT(20))

    dfam_taxdb_tax = relationship('DfamTaxdb')


class Classification(Base):
    __tablename__ = 'classification'

    id = Column(BIGINT(20), primary_key=True)
    parent_id = Column(BIGINT(20))
    name = Column(String(80), nullable=False)
    tooltip = Column(String(128))
    description = Column(Text)
    hyperlink = Column(String(255))
    repeatmasker_type_id = Column(ForeignKey('repeatmasker_type.id'), index=True)
    repeatmasker_subtype_id = Column(ForeignKey('repeatmasker_subtype.id'), index=True)
    sort_order = Column(INTEGER(8))
    repbase_equiv = Column(String(255))
    wicker_equiv = Column(String(255))
    curcio_derbyshire_equiv = Column(String(255))
    piegu_equiv = Column(String(255))
    lineage = Column(Text)
    aliases = Column(Text)

    repeatmasker_subtype = relationship('RepeatmaskerSubtype')
    repeatmasker_type = relationship('RepeatmaskerType')


t_classification_has_wikipedia = Table(
    'classification_has_wikipedia', metadata,
    Column('classification_id', ForeignKey('classification.id'), primary_key=True, nullable=False, index=True),
    Column('auto_wiki', ForeignKey('wikipedia.auto_wiki'), primary_key=True, nullable=False, index=True)
)


class Family(Base):
    __tablename__ = 'family'

    id = Column(BIGINT(20), primary_key=True, unique=True)
    accession = Column(String(45), unique=True)
    version = Column(SMALLINT(5), server_default=text("'1'"))
    name = Column(String(45), unique=True)
    classification_id = Column(ForeignKey('classification.id'), index=True)
    description = Column(Text)
    consensus = Column(Text)
    date_created = Column(DateTime)
    date_modified = Column(DateTime)
    date_deleted = Column(DateTime)
    target_site_cons = Column(String(30))
    author = Column(TINYTEXT)
    deposited_by_id = Column(INTEGER(11))
    curation_state_id = Column(ForeignKey('curation_state.id'), index=True)
    disabled = Column(TINYINT(1), server_default=text("'0'"))
    refineable = Column(TINYINT(1), server_default=text("'0'"))
    model_consensus = Column(Text)
    model_mask = Column(Text)
    hmm_build_method_id = Column(BIGINT(20))
    cons_build_method_id = Column(BIGINT(20))
    length = Column(INTEGER(11))
    hmm_maxl = Column(INTEGER(11))
    hmm_general_threshold = Column(Float(asdecimal=True))
    seed_ref = Column(MEDIUMTEXT)
    title = Column(String(80))
    curation_notes = Column(Text)
    source_method_id = Column(ForeignKey('source_method.id'), index=True)
    source_method_desc = Column(Text)
    source_assembly_id = Column(ForeignKey('assembly.id'), index=True)

    classification = relationship('Classification')
    curation_state = relationship('CurationState')
    source_assembly = relationship('Assembly')
    source_method = relationship('SourceMethod')
    repeatmasker_stages = relationship('RepeatmaskerStage', secondary='family_has_search_stage')


class CodingSequence(Base):
    __tablename__ = 'coding_sequence'

    id = Column(BIGINT(20), primary_key=True)
    product = Column(String(45), nullable=False, unique=True)
    translation = Column(Text, nullable=False)
    cds_start = Column(INTEGER(10))
    cds_end = Column(INTEGER(10))
    exon_count = Column(INTEGER(10))
    exon_starts = Column(LONGBLOB)
    exon_ends = Column(LONGBLOB)
    family_id = Column(ForeignKey('family.id'), index=True)
    external_reference = Column(String(128))
    reverse = Column(TINYINT(1))
    stop_codons = Column(INTEGER(11))
    frameshifts = Column(INTEGER(11))
    gaps = Column(INTEGER(11))
    percent_identity = Column(Float)
    left_unaligned = Column(INTEGER(11))
    right_unaligned = Column(INTEGER(11))
    classification_id = Column(BIGINT(20))
    align_data = Column(Text)
    description = Column(Text)
    protein_type = Column(String(45))

    family = relationship('Family')


class FamilyAssemblyDatum(Base):
    __tablename__ = 'family_assembly_data'
    __table_args__ = (
        Index('family_assembly_data_UNIQUE', 'family_id', 'assembly_id', unique=True),
    )

    family_id = Column(ForeignKey('family.id'), primary_key=True, nullable=False)
    assembly_id = Column(ForeignKey('assembly.id'), primary_key=True, nullable=False, index=True)
    cons_genome_avg_kimura_div_GA = Column(Float)
    cons_genome_avg_kimura_div_TC = Column(Float)
    hmm_genome_avg_kimura_div_GA = Column(Float)
    hmm_genome_avg_kimura_div_TC = Column(Float)
    cons_GA_hit_count = Column(BIGINT(20))
    cons_TC_hit_count = Column(BIGINT(20))
    cons_GA_nrph_hit_count = Column(BIGINT(20))
    cons_TC_nrph_hit_count = Column(BIGINT(20))
    hmm_GA_hit_count = Column(BIGINT(20))
    hmm_TC_hit_count = Column(BIGINT(20))
    hmm_GA_nrph_hit_count = Column(BIGINT(20))
    hmm_TC_nrph_hit_count = Column(BIGINT(20))
    hmm_hit_GA = Column(Float(asdecimal=True))
    hmm_hit_GA_evalue = Column(String(15))
    hmm_hit_TC = Column(Float(asdecimal=True))
    hmm_hit_TC_evalue = Column(String(15))
    hmm_hit_NC = Column(Float(asdecimal=True))
    hmm_hit_NC_evalue = Column(String(15))
    hmm_fdr = Column(Float(asdecimal=True))
    hmm_method_id = Column(INTEGER(10))
    cons_fdr = Column(Float(asdecimal=True))
    cons_method_id = Column(INTEGER(10))
    cons_35GC_GA = Column(INTEGER(10))
    cons_37GC_GA = Column(INTEGER(10))
    cons_39GC_GA = Column(INTEGER(10))
    cons_41GC_GA = Column(INTEGER(10))
    cons_43GC_GA = Column(INTEGER(10))
    cons_45GC_GA = Column(INTEGER(10))
    cons_47GC_GA = Column(INTEGER(10))
    cons_49GC_GA = Column(INTEGER(10))
    cons_51GC_GA = Column(INTEGER(10))
    cons_53GC_GA = Column(INTEGER(10))
    cons_matrix_div = Column(INTEGER(10))
    hmm_avg_hit_length = Column(INTEGER(10))
    cons_avg_hit_length = Column(INTEGER(10))
    hmm_thresh_search_evalue = Column(String(15))

    assembly = relationship('Assembly')
    family = relationship('Family')


t_family_clade = Table(
    'family_clade', metadata,
    Column('family_id', ForeignKey('family.id'), primary_key=True, nullable=False, index=True),
    Column('dfam_taxdb_tax_id', ForeignKey('dfam_taxdb.tax_id'), primary_key=True, nullable=False, index=True)
)


class FamilyDatabaseAlia(Base):
    __tablename__ = 'family_database_alias'

    family_id = Column(ForeignKey('family.id'), primary_key=True, nullable=False, index=True)
    db_id = Column(String(80), primary_key=True, nullable=False)
    db_link = Column(String(80), primary_key=True, nullable=False)
    deprecated = Column(TINYINT(1), server_default=text("'0'"))
    comment = Column(Text)

    family = relationship('Family')


class FamilyFeature(Base):
    __tablename__ = 'family_feature'

    id = Column(BIGINT(20), primary_key=True)
    family_id = Column(ForeignKey('family.id'), index=True)
    feature_type = Column(String(45))
    description = Column(Text)
    model_start_pos = Column(INTEGER(10))
    model_end_pos = Column(INTEGER(10))
    label = Column(String(45))

    family = relationship('Family')


class FamilyHasBufferStage(Base):
    __tablename__ = 'family_has_buffer_stage'

    family_id = Column(ForeignKey('family.id'), primary_key=True, nullable=False)
    repeatmasker_stage_id = Column(ForeignKey('repeatmasker_stage.id'), primary_key=True, nullable=False, index=True)
    start_pos = Column(MEDIUMINT(8), primary_key=True, nullable=False)
    end_pos = Column(MEDIUMINT(8), primary_key=True, nullable=False)

    family = relationship('Family')
    repeatmasker_stage = relationship('RepeatmaskerStage')


class FamilyHasCitation(Base):
    __tablename__ = 'family_has_citation'

    family_id = Column(ForeignKey('family.id'), primary_key=True, nullable=False)
    citation_pmid = Column(ForeignKey('citation.pmid', ondelete='CASCADE'), primary_key=True, nullable=False, index=True)
    comment = Column(TINYTEXT)
    order_added = Column(TINYINT(4))

    citation = relationship('Citation')
    family = relationship('Family')


t_family_has_search_stage = Table(
    'family_has_search_stage', metadata,
    Column('family_id', ForeignKey('family.id'), primary_key=True, nullable=False),
    Column('repeatmasker_stage_id', ForeignKey('repeatmasker_stage.id'), primary_key=True, nullable=False, index=True)
)


class FamilyOverlap(Base):
    __tablename__ = 'family_overlap'

    id = Column(BIGINT(20), primary_key=True)
    family1_id = Column(ForeignKey('family.id'), nullable=False, index=True)
    family2_id = Column(ForeignKey('family.id'), nullable=False, index=True)

    family1 = relationship('Family', primaryjoin='FamilyOverlap.family1_id == Family.id')
    family2 = relationship('Family', primaryjoin='FamilyOverlap.family2_id == Family.id')


class HmmModelDatum(Base):
    __tablename__ = 'hmm_model_data'

    family_id = Column(ForeignKey('family.id'), primary_key=True)
    hmm_logo = Column(LONGBLOB)
    hmm = Column(LONGBLOB)

    family = relationship('Family', uselist=False)


class SeedAlignDatum(Base):
    __tablename__ = 'seed_align_data'

    family_id = Column(ForeignKey('family.id'), primary_key=True)
    graph_json = Column(LONGBLOB, nullable=False)
    avg_kimura_divergence = Column(Float)

    family = relationship('Family', uselist=False)


t_seed_region = Table(
    'seed_region', metadata,
    Column('family_id', ForeignKey('family.id'), nullable=False, index=True),
    Column('assembly_id', ForeignKey('assembly.id'), nullable=False, index=True),
    Column('seq_id', String(128), nullable=False),
    Column('seq_start', BIGINT(20)),
    Column('seq_end', BIGINT(20)),
    Column('a3m_seq', Text, nullable=False),
    Column('strand', Enum('+', '-')),
    Column('model_start', MEDIUMINT(8), nullable=False),
    Column('model_end', MEDIUMINT(8), nullable=False)
)


class FeatureAttribute(Base):
    __tablename__ = 'feature_attribute'

    family_feature_id = Column(ForeignKey('family_feature.id'), primary_key=True, nullable=False)
    attribute = Column(String(45), primary_key=True, nullable=False, unique=True)
    value = Column(String(45))

    family_feature = relationship('FamilyFeature')


class OverlapSegment(Base):
    __tablename__ = 'overlap_segment'

    family_overlap_id = Column(ForeignKey('family_overlap.id'), primary_key=True, nullable=False, index=True)
    family1_start = Column(MEDIUMINT(8), primary_key=True, nullable=False)
    family1_end = Column(MEDIUMINT(8), primary_key=True, nullable=False)
    family2_start = Column(MEDIUMINT(8), primary_key=True, nullable=False)
    family2_end = Column(MEDIUMINT(8), primary_key=True, nullable=False)
    strand = Column(Enum('+', '-'), primary_key=True, nullable=False)
    evalue = Column(String(15))
    identity = Column(String(6))
    coverage = Column(String(6))
    cigar = Column(Text)

    family_overlap = relationship('FamilyOverlap')
