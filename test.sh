#!/usr/bin/bash

set -u -o pipefail

show_run() {
	echo ">" "$@"
	"$@"
}

basename="Dfam_partial"
h5name="${basename}_test.h5"

if [ ! -e "$h5name" ]; then
	show_run ./convert_hmm.py import -t ncbi_tax -e taxonomy.list "test_data/${basename}.hmm" "$h5name"
fi

dumpname="${h5name}.dump.hmm"
show_run ./convert_hmm.py dump "$h5name" "$dumpname"
show_run diff -u "$dumpname" "test_data/expected_$dumpname" | head || exit 1
show_run rm "$dumpname"

show_run ./famdb.py query "$h5name" names mus
show_run ./famdb.py query "$h5name" lineage -d 9605
show_run ./famdb.py query "$h5name" lineage -a 40674
show_run ./famdb.py query "$h5name" lineage -d 40674
