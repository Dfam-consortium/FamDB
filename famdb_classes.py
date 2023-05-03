import datetime
import time
import re
import os
import json
import sys

import h5py
import numpy

from famdb_helper_classes import Family
from famdb_globals import LOGGER, FILE_VERSION
from famdb_helper_methods import sanitize_name, sounds_like


class FamDB:
    """Transposable Element Family and taxonomy database."""

    dtype_str = h5py.special_dtype(vlen=str)

    GROUP_FAMILIES = "Families"
    GROUP_FAMILIES_BYNAME = "Families/ByName"
    GROUP_FAMILIES_BYACC = "Families/ByAccession"
    GROUP_FAMILIES_BYSTAGE = "Families/ByStage"
    GROUP_NODES = "Taxonomy/Nodes"
    GROUP_TAXANAMES = "TaxaNames"

    # DF####### or DF########## or DR####### or DR##########
    dfam_acc_pat = re.compile("^(D[FR])([0-9]{2})([0-9]{2})[0-9]{3,6}$")

    def __init__(self, filename, mode="r"):
        if mode == "r":
            reading = True

            # If we definitely will not be writing to the file, optimistically assume
            # nobody else is writing to it and disable file locking. File locking can
            # be a bit flaky, especially on NFS, and is unnecessary unless there is
            # a parallel writer (which is unlikely for famdb files).
            os.environ["HDF5_USE_FILE_LOCKING"] = "FALSE"

        elif mode == "r+":
            reading = True
        elif mode == "w":
            reading = False
        else:
            raise ValueError(
                "Invalid file mode. Expected 'r' or 'r+' or 'w', got '{}'".format(mode)
            )

        self.filename = filename
        self.file = h5py.File(filename, mode)
        self.mode = mode

        try:
            if reading and self.file.attrs["version"] != FILE_VERSION:
                raise Exception(
                    "File version is {}, but this is version {}".format(
                        self.file.attrs["version"],
                        FILE_VERSION,
                    )
                )
        except:
            # This 'except' catches both "version" missing from attrs, or the
            # value not matching if it is present.
            raise Exception("This file cannot be read by this version of famdb.py.")

        self.__lineage_cache = {}

        if self.mode == "w":
            self.seen = {}
            self.added = {"consensus": 0, "hmm": 0}
            self.__write_metadata()
        elif self.mode == "r+":
            self.seen = {}
            self.seen["name"] = set(self.file[FamDB.GROUP_FAMILIES_BYNAME].keys())
            self.seen["accession"] = set(
                self.__families_iterator(self.file[FamDB.GROUP_FAMILIES], "Families")
            )
            self.added = self.get_counts()

    # Export Setters ----------------------------------------------------------------------------------------------------
    def set_partition_info(self, partition_num):
        """Sets partition number (key to file info) and bool if is root file or not"""
        self.file.attrs["partition_num"] = partition_num
        self.file.attrs["root"] = partition_num == "0" or partition_num == 0

    def set_file_info(self, map_str):
        """Stores information about other files as json string"""
        self.file.attrs["file_info"] = json.dumps(map_str)

    def set_db_info(self, name, version, date, desc, copyright_text):
        """Sets database metadata for the current file"""
        self.file.attrs["db_name"] = name
        self.file.attrs["db_version"] = version
        self.file.attrs["db_date"] = date
        self.file.attrs["db_description"] = desc
        self.file.attrs["db_copyright"] = copyright_text

    def __write_metadata(self):
        """Sets file data during writing"""
        self.file.attrs["generator"] = f"famdb.py v{FILE_VERSION}"
        self.file.attrs["version"] = FILE_VERSION
        self.file.attrs["created"] = str(datetime.datetime.now())

    def finalize(self):
        """Writes some collected metadata, such as counts, to the database"""
        self.file.attrs["count_consensus"] = self.added["consensus"]
        self.file.attrs["count_hmm"] = self.added["hmm"]

    # Attribute Getters -----------------------------------------------------------------------------------------------
    def get_partition_num(self):
        """Partition num is used as the key in file_info"""
        return self.file.attrs["partition_num"]

    def get_file_info(self):
        """returns dictionary containing information regarding other related files"""
        return json.loads(self.file.attrs["file_info"])

    def is_root(self):
        """Tests if file is root file"""  # TODO remove to subclass
        return self.file.attrs["root"]

    def get_db_info(self):
        """
        Gets database database metadata for the current file as a dict with keys
        'name', 'version', 'date', 'description', 'copyright'
        """
        if "db_name" not in self.file.attrs:
            return None

        return {
            "name": self.file.attrs["db_name"],
            "version": self.file.attrs["db_version"],
            "date": self.file.attrs["db_date"],
            "description": self.file.attrs["db_description"],
            "copyright": self.file.attrs["db_copyright"],
        }

    def get_metadata(self):
        """
        Gets file metadata for the current file as a dict with keys
        'generator', 'version', 'created', 'partition_name', 'partition_detail'
        """
        num = self.file.attrs["partition_num"]
        partition = self.get_file_info()["file_map"][str(num)]
        return {
            "generator": self.file.attrs["generator"],
            "version": self.file.attrs["version"],
            "created": self.file.attrs["created"],
            "partition_name": partition["T_root_name"],
            "partition_detail": ", ".join(partition["F_roots_names"]),
        }

    def get_counts(self):
        """
        Gets counts of entries in the current file as a dict
        with 'consensus', 'hmm'
        """
        return {
            "consensus": self.file.attrs["count_consensus"],
            "hmm": self.file.attrs["count_hmm"],
        }

    # File Utils
    def close(self):
        """Closes this FamDB instance, making further use invalid."""
        self.file.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    # Data Writing Methods ---------------------------------------------------------------------------------------------
    # Family Methods
    def __check_unique(self, family, key):
        """Verifies that 'family' is uniquely identified by its value of 'key'."""

        seen = self.seen
        value = getattr(family, key)
        if key not in seen:
            seen[key] = set()

        if value in seen[key]:
            raise Exception(
                "Family is not unique! Already seen {}: {}".format(key, value)
            )

        seen[key].add(value)

    @staticmethod
    def __accession_bin(acc):
        """Maps an accession (Dfam or otherwise) into apropriate bins (groups) in HDF5"""
        dfam_match = FamDB.dfam_acc_pat.match(acc)
        if dfam_match:
            path = (
                FamDB.GROUP_FAMILIES
                + "/"
                + dfam_match.group(1)
                + "/"
                + dfam_match.group(2)
                + "/"
                + dfam_match.group(3)
            )
        else:
            path = FamDB.GROUP_FAMILIES + "/Aux/" + acc[0:2].lower()
        return path

    @staticmethod
    def __families_iterator(g, prefix=""):
        for key, item in g.items():
            path = "{}/{}".format(prefix, key)
            if isinstance(item, h5py.Dataset):  # test for dataset
                yield (key)
            elif isinstance(item, h5py.Group):  # test for group (go down)
                yield from FamDB.__families_iterator(item, path)

    def add_family(self, family):
        """Adds the family described by 'family' to the database."""
        # Verify uniqueness of name and accession.
        # This is important because of the links created to them later.
        if family.name:
            self.__check_unique(family, "name")
        self.__check_unique(family, "accession")

        # Increment counts
        if family.consensus:
            self.added["consensus"] += 1
        if family.model:
            self.added["hmm"] += 1

        # Create the family data
        # In v0.5 we bin the datasets into subgroups to improve performance
        group_path = self.__accession_bin(family.accession)
        dset = self.file.require_group(group_path).create_dataset(
            family.accession, (0,)
        )

        # Set the family attributes
        for k in Family.META_LOOKUP:
            value = getattr(family, k)
            if value:
                dset.attrs[k] = value

        # Create links
        if family.name:
            self.file.require_group(FamDB.GROUP_FAMILIES_BYNAME)[
                family.name
            ] = h5py.SoftLink(group_path + "/" + family.accession)
        # In FamDB format version 0.5 we removed the /Families/ByAccession group as it's redundant
        # (all the data is in Families/<datasets> *and* HDF5 suffers from poor performance when
        # the number of entries in a group exceeds 200-500k.

        for clade_id in family.clades:
            taxon_group = self.file.require_group(FamDB.GROUP_NODES).require_group(
                str(clade_id)
            )
            families_group = taxon_group.require_group("Families")
            families_group[family.accession] = h5py.SoftLink(
                group_path + "/" + family.accession
            )

        def add_stage_link(stage, accession):
            stage_group = self.file.require_group(
                FamDB.GROUP_FAMILIES_BYSTAGE
            ).require_group(stage.strip())
            if accession not in stage_group:
                stage_group[accession] = h5py.SoftLink(group_path + "/" + accession)

        if family.search_stages:
            for stage in family.search_stages.split(","):
                add_stage_link(stage, family.accession)

        if family.buffer_stages:
            for stage in family.buffer_stages.split(","):
                stage = stage.split("[")[0]
                add_stage_link(stage, family.accession)

        LOGGER.debug("Added family %s (%s)", family.name, family.accession)

    # Taxonomy Nodes
    def write_taxonomy(self, tax_db, nodes):
        """Writes taxonomy nodes in 'nodes' to the database."""
        LOGGER.info("Writing taxonomy nodes")
        start = time.perf_counter()

        count = 0
        for node in nodes:
            count += 1
            group = self.file.require_group(FamDB.GROUP_NODES).require_group(
                str(tax_db[node].tax_id)
            )
            parent_id = int(tax_db[node].parent_id) if tax_db[node].parent_id else None
            if parent_id:
                group.create_dataset("Parent", data=numpy.array([parent_id]))

            child_ids = []
            for child in tax_db[node].children:
                child_ids += [int(child.tax_id)]
            group.create_dataset("Children", data=numpy.array(child_ids))
        delta = time.perf_counter() - start
        LOGGER.info("Wrote %d taxonomy nodes in %f", count, delta)

    # Data Access Methods ------------------------------------------------------------------------------------------------
    def has_taxon(self, tax_id):
        """Returns True if 'self' has a taxonomy entry for 'tax_id'"""
        # test if file has families or just taxonomy info
        return (
            str(tax_id) in self.file[FamDB.GROUP_NODES]
            and "Families" in self.file[FamDB.GROUP_NODES][str(tax_id)]
        )

    def get_families_for_taxon(self, tax_id, root_file=None):
        """Returns a list of the accessions for each family directly associated with 'tax_id'."""
        group = self.file[FamDB.GROUP_NODES][str(tax_id)].get("Families")
        if group:
            return list(group.keys())

    def get_lineage(self, tax_id, **kwargs):
        """
        Returns the lineage of 'tax_id'. Recognized kwargs: 'descendants' to include
        descendant taxa, 'ancestors' to include ancestor taxa.
        IDs are returned as a nested list, for example
        [ 1, [ 2, [3, [4]], [5], [6, [7]] ] ]
        where '2' may have been the passed-in 'tax_id'.
        """

        group_nodes = self.file[FamDB.GROUP_NODES]

        if kwargs.get("descendants"):

            def descendants_of(tax_id):
                descendants = [int(tax_id)]
                for child in group_nodes[str(tax_id)]["Children"]:
                    descendants += [descendants_of(child)]
                return descendants

            tree = descendants_of(tax_id)
        else:
            tree = [tax_id]

        if kwargs.get("ancestors"):
            while tax_id:
                node = group_nodes[str(tax_id)]
                if "Parent" in node:
                    tax_id = node["Parent"][0]
                    tree = [tax_id, tree]
                else:
                    tax_id = None

        return tree

    # Filter methods --------------------------------------------------------------------------
    @staticmethod
    def __filter_name(family, name):
        """Returns True if the family's name begins with 'name'."""

        if family.attrs.get("name"):
            if family.attrs["name"].lower().startswith(name):
                return True

        return False

    def __filter_stages(self, accession, stages):
        """Returns True if the family belongs to a search or buffer stage in 'stages'."""
        for stage in stages:
            grp = self.file[FamDB.GROUP_FAMILIES_BYSTAGE].get(stage)
            if grp and accession in grp:
                return True

        return False

    @staticmethod
    def __filter_search_stages(family, stages):
        """Returns True if the family belongs to a search stage in 'stages'."""
        if family.attrs.get("search_stages"):
            sstages = (ss.strip() for ss in family.attrs["search_stages"].split(","))
            for family_ss in sstages:
                if family_ss in stages:
                    return True

        return False

    @staticmethod
    def __filter_repeat_type(family, rtype):
        """
        Returns True if the family's RepeatMasker Type plus SubType
        (e.g. "DNA/CMC-EnSpm") starts with 'rtype'.
        """
        if family.attrs.get("repeat_type"):
            full_type = family.attrs["repeat_type"]
            if family.attrs.get("repeat_subtype"):
                full_type = full_type + "/" + family.attrs["repeat_subtype"]

            if full_type.lower().startswith(rtype):
                return True

        return False

    @staticmethod
    def __filter_curated(accession, curated):
        """
        Returns True if the family's curatedness is the same as 'curated'. In
        other words, 'curated=True' includes only curated familes and
        'curated=False' includes only uncurated families.

        Families are currently assumed to be curated unless their name is of the
        form DR<7 digits>.

        TODO: perhaps this should be a dedicated 'curated' boolean field on Family
        """

        is_curated = not (
            accession.startswith("DR")
            and len(accession) == 9
            and all((c >= "0" and c <= "9" for c in accession[2:]))
        )

        return is_curated == curated

    def get_accessions_filtered(self, **kwargs):
        """
        Returns an iterator that yields accessions for the given search terms.

        Filters are specified in kwargs:
            tax_id: int
            ancestors: boolean, default False
            descendants: boolean, default False
                If none of (tax_id, ancestors, descendants) are
                specified, *all* families will be checked.
            curated_only = boolean
            uncurated_only = boolean
            stage = int
            is_hmm = boolean
            repeat_type = string (prefix)
            name = string (prefix)
                If any of stage, repeat_type, or name are
                omitted (or None), they will not be used to filter.

                The behavior of 'stage' depends on 'is_hmm': if is_hmm is True,
                stage must match in SearchStages (a match in BufferStages is not
                enough).
        """

        if not ("tax_id" in kwargs or "ancestors" in kwargs or "descendants" in kwargs):
            tax_id = 1
            ancestors = True
            descendants = True
        else:
            tax_id = kwargs["tax_id"]
            ancestors = kwargs.get("ancestors") or False
            descendants = kwargs.get("descendants") or False

        # Define family filters (logically ANDed together)
        filters = []

        if kwargs.get("curated_only"):
            filters += [lambda a, f: self.__filter_curated(a, True)]
        if kwargs.get("uncurated_only"):
            filters += [lambda a, f: self.__filter_curated(a, False)]

        filter_stage = kwargs.get("stage")
        filter_stages = None
        if filter_stage:
            if filter_stage == 80:
                # "stage 80" = "all stages", so skip filtering
                pass
            elif filter_stage == 95:
                # "stage 95" = this specific stage list:
                filter_stages = ["35", "50", "55", "60", "65", "70", "75"]
                filters += [lambda a, f: self.__filter_stages(a, filter_stages)]
            else:
                filter_stages = [str(filter_stage)]
                filters += [lambda a, f: self.__filter_stages(a, filter_stages)]

        # HMM only: add a search stage filter to "un-list" families that were
        # allowed through only because they match in buffer stage
        if kwargs.get("is_hmm") and filter_stages:
            filters += [lambda a, f: self.__filter_search_stages(f(), filter_stages)]

        filter_repeat_type = kwargs.get("repeat_type")
        if filter_repeat_type:
            filter_repeat_type = filter_repeat_type.lower()
            filters += [lambda a, f: self.__filter_repeat_type(f(), filter_repeat_type)]

        filter_name = kwargs.get("name")
        if filter_name:
            filter_name = filter_name.lower()
            filters += [lambda a, f: self.__filter_name(f(), filter_name)]

        # Recursive iterator flattener
        def walk_tree(tree):
            """Returns all elements in 'tree' with all levels flattened."""
            if hasattr(tree, "__iter__"):
                for elem in tree:
                    yield from walk_tree(elem)
            else:
                yield tree

        seen = set()

        def iterate_accs():
            # special case: Searching the whole database in a specific
            # stage only is a common usage pattern in RepeatMasker.
            # When searching the whole database instead of a species,
            # the number of accessions to read through is shorter
            # when going off of only the stage indexes.
            if (
                tax_id == 1
                and descendants
                and filter_stages
                and not filter_repeat_type
                and not filter_name
            ):
                for stage in filter_stages:
                    grp = self.file[FamDB.GROUP_FAMILIES_BYSTAGE].get(stage)
                    if grp:
                        yield from grp.keys()

            # special case: Searching the whole database, going directly via
            # Families/ is faster than repeatedly traversing the tree
            elif tax_id == 1 and descendants:
                # yield from self.file[FamDB.GROUP_FAMILIES_BYACC].keys()
                for name in self.__families_iterator(
                    self.file[FamDB.GROUP_FAMILIES], "Families"
                ):
                    yield name
            else:
                lineage = self.get_lineage(
                    tax_id, ancestors=ancestors, descendants=descendants
                )
                for node in walk_tree(lineage):
                    yield from self.get_families_for_taxon(node)

        for accession in iterate_accs():
            if accession in seen:
                continue
            seen.add(accession)

            cached_family = None

            def family_getter():
                nonlocal cached_family
                if not cached_family:
                    path = self.__accession_bin(accession)
                    cached_family = self.file[path].get(accession)
                return cached_family

            match = True
            for filt in filters:
                if not filt(accession, family_getter):
                    match = False
            if match:
                yield accession

    # Family Getters --------------------------------------------------------------------------
    def get_family_names(self):
        """Returns a list of names of families in the database."""
        return sorted(self.file[FamDB.GROUP_FAMILIES_BYNAME].keys(), key=str.lower)

    @staticmethod
    def __get_family(entry):
        if not entry:
            return None

        family = Family()

        # Read the family attributes and data
        for k in entry.attrs:
            value = entry.attrs[k]
            setattr(family, k, value)

        return family

    def get_family_by_accession(self, accession):
        """Returns the family with the given accession."""
        path = self.__accession_bin(accession)
        if path in self.file:
            entry = self.file[path].get(accession)
            return self.__get_family(entry)
        return None

    def get_family_by_name(self, name):
        """Returns the family with the given name."""
        # TODO: This will also suffer the performance issues seen with
        #       other groups that exceed 200-500k entries in a single group
        #       at some point.  This needs to be refactored to scale appropriately.
        entry = self.file[FamDB.GROUP_FAMILIES_BYNAME].get(name)
        return self.__get_family(entry)


class FamDBRoot(FamDB):
    def __init__(self, filename, mode="r"):
        super(FamDBRoot, self).__init__(filename, mode)

        if mode == "r" or mode == "r+":
            self.names_dump = {
                partition: json.loads(
                    self.file[f"{FamDBRoot.GROUP_TAXANAMES}/{partition}"]["TaxaNames"][
                        0
                    ]
                )
                for partition in self.file[FamDBRoot.GROUP_TAXANAMES]
            }

    def write_taxa_names(self, tax_db, nodes):
        LOGGER.info("Writing TaxaNames")
        for partition in nodes:
            taxnames_group = self.file.require_group(
                FamDB.GROUP_TAXANAMES + f"/{partition}"
            )
            names_dump = {}
            for node in nodes[partition]:
                names_dump[node] = tax_db[node].names
            names_data = numpy.array([json.dumps(names_dump)])
            names_dset = taxnames_group.create_dataset(
                "TaxaNames", shape=names_data.shape, dtype=FamDB.dtype_str
            )
            names_dset[:] = names_data

    def get_taxon_names(self, tax_id):
        """
        Checks names_dump for each partition and returns a list of [name_class, name_value, partition]
        of the taxon given by 'tax_id'.
        """
        names_list = []
        for partition in self.names_dump:
            names = self.names_dump[partition].get(str(tax_id))
            if names:
                names += [int(partition)]
                names_list += names
        return names_list

    def get_taxon_name(self, tax_id, kind="scientific name"):
        """
        Checks names_dump for each partition and returns eturns the first name of the given 'kind'
        for the taxon given by 'tax_id', or None if no such name was found.
        """
        for partition in self.names_dump:
            names = self.names_dump[partition].get(str(tax_id))
            if names:
                for name in names:
                    if name[0] == kind:
                        return [name[1], int(partition)]
        return None

    def search_taxon_names(self, text, kind=None, search_similar=False):
        """
        Searches 'self' for taxons with a name containing 'text', returning an
        iterator that yields a tuple of (id, is_exact, partition) for each matching node.
        Each id is returned at most once, and if any of its names are an exact
        match the whole node is treated as an exact match.

        If 'similar' is True, names that sound similar will also be considered
        eligible.

        A list of strings may be passed as 'kind' to restrict what kinds of
        names will be searched.
        """

        text = text.lower()
        for partition in self.names_dump:
            for tax_id, names in self.names_dump[partition].items():
                matches = False
                exact = False
                for name_cls, name_txt in names:
                    name_txt = name_txt.lower()
                    if kind is None or kind == name_cls:
                        if text == name_txt:
                            matches = True
                            exact = True
                        elif name_txt.startswith(text + " <"):
                            matches = True
                            exact = True
                        elif text == sanitize_name(name_txt):
                            matches = True
                            exact = True
                        elif text in name_txt:
                            matches = True
                        elif search_similar and sounds_like(text, name_txt):
                            matches = True

                if matches:
                    yield [int(tax_id), exact, int(partition)]

    def resolve_species(self, term, kind=None, search_similar=False):
        """
        Resolves 'term' as a species or clade in 'self'. If 'term' is a number,
        it is a taxon id. Otherwise, it will be searched for in 'self' in the
        name fields of all taxa. A list of strings may be passed as 'kind' to
        restrict what kinds of names will be searched.

        If 'search_similar' is True, a "sounds like" search will be tried
        first. If it is False, a "sounds like" search will still be performed

        if no results were found.

        This function returns a list of tuples (taxon_id, is_exact) that match
        the query. The list will be empty if no matches were found.
        """

        # Try as a number
        try:
            tax_id = int(term)
            if self.has_taxon(tax_id):
                return [[tax_id, True]]

            return []
        except ValueError:
            pass

        # Perform a search by name, splitting between exact and inexact matches for sorting
        exact = []
        inexact = []
        for tax_id, is_exact in self.search_taxon_names(term, kind, search_similar):
            if is_exact:
                exact += [tax_id]
            else:
                inexact += [tax_id]

        # Combine back into one list, with exact matches first
        results = [[tax_id, True] for tax_id in exact]
        for tax_id in inexact:
            results += [[tax_id, False]]

        if len(results) == 0 and not search_similar:
            # Try a sounds-like search (currently soundex)
            similar_results = self.resolve_species(term, kind, True)
            if similar_results:
                print(
                    "No results were found for that name, but some names sound similar:",
                    file=sys.stderr,
                )
                for tax_id, _ in similar_results:
                    names = self.get_taxon_names(tax_id)
                    print(
                        tax_id,
                        ", ".join(["{1}".format(*n) for n in names]),
                        file=sys.stderr,
                    )

        return results

    def resolve_one_species(self, term, kind=None):
        """
        Resolves 'term' in 'dbfile' as a taxon id or search term unambiguously.
        Parameters are as in the 'resolve_species' method.
        Returns None if not exactly one result is found,
        and prints details to the screen.
        """

        results = self.resolve_species(term, kind)

        # Check for a single exact match first, to any field
        exact_matches = []
        for nid, is_exact in results:
            if is_exact:
                exact_matches += [nid]
        if len(exact_matches) == 1:
            return exact_matches[0]

        if len(results) == 1:
            return results[0][0]
        elif len(results) > 1:
            print(
                """Ambiguous search term '{}' (found {} results, {} exact).
Please use a more specific name or taxa ID, which can be looked
up with the 'names' command.""".format(
                    term, len(results), len(exact_matches)
                ),
                file=sys.stderr,
            )

        return None

    def get_sanitized_name(self, tax_id):
        """
        Returns the "sanitized name" of tax_id, which is the sanitized version
        of the scientific name.
        """

        name = self.get_taxon_name(tax_id, "scientific name")
        if name:
            name = sanitize_name(name)
        return name

    def get_lineage_path(self, tax_id, cache=True):
        """
        Returns a list of strings encoding the lineage for 'tax_id'.
        """

        if cache and tax_id in self.__lineage_cache:
            return self.__lineage_cache[tax_id]

        tree = self.get_lineage(tax_id, ancestors=True)
        lineage = []

        while tree:
            node = tree[0]
            tree = tree[1] if len(tree) > 1 else None

            tax_name = self.get_taxon_name(node, "scientific name")
            lineage += [tax_name]

        if cache:
            self.__lineage_cache[tax_id] = lineage

        return lineage

    def find_files(self):
        # repbase_file = "./partitions/RMRB_spec_to_tax.json" TODO
        file_info = self.get_file_info()
        meta = file_info["meta"]
        file_map = file_info["file_map"]
        files = {}
        for file in file_map:
            partition_name = file_map[file]["T_root_name"]
            partition_detail = file_map[file]["F_roots_names"]
            filename = file_map[file]["filename"]
            counts = None
            status = "Missing"
            if os.path.isfile(filename):
                checkfile = FamDB(filename, "r")
                db_info = checkfile.get_db_info()
                same_dfam, same_partition = False, False
                # test if database versions were the same
                if (
                    meta["db_version"] == db_info["version"]
                    and meta["db_date"] == db_info["date"]
                ):
                    same_dfam = True
                # test if files are from the same partitioning run
                if meta["id"] == checkfile.get_file_info()["meta"]["id"]:
                    same_partition = True
                # update status
                if not same_partition:
                    status = "File From Different Partition"
                elif not same_dfam:
                    status = "File From Previous Dfam Release"
                else:
                    status = "Present"
                    counts = checkfile.get_counts()
                files[file] = {
                    "partition_name": partition_name,
                    "partition_detail": partition_detail,
                    "filename": filename,
                    "counts": counts,
                    "status": status,
                }
        return files
