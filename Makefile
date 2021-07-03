.PHONY: check coverage

check:
	python3 -m unittest

coverage:
	FAMDB_TEST_COVERAGE=1 coverage run -m unittest
	coverage combine
	coverage html --omit='*/site-packages/*'
